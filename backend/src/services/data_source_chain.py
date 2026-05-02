# -*- coding: utf-8 -*-
"""
===================================
数据源优先级链管理器 (DataSourceChain)
===================================

为每个数据类别（标的列表、K线、实时行情）维护一个有序数据源队列。
请求时从最高优先级源开始尝试，若失败则自动降级到下一级。

健康检查：
- 成功请求时标记为健康
- 失败时记录次数，触发指数退避
- 权限/配额错误 vs 临时错误区分处理
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AllSourcesFailedError(Exception):
    """所有数据源均不可用"""

    def __init__(self, category: str, errors: Optional[List[str]] = None):
        self.category = category
        self.errors = errors or []
        detail = "; ".join(self.errors) if self.errors else "无详情"
        super().__init__(f"[{category}] 所有数据源均失败: {detail}")


@dataclass
class _SourceHealth:
    """单个数据源的健康状态"""
    healthy: bool = True
    fail_count: int = 0
    last_fail_at: float = 0.0
    last_error: str = ""
    permanent_skip: bool = False  # 权限/认证错误时永久跳过


@dataclass
class DataSource:
    """一个数据源适配器描述"""
    name: str
    fetch: Callable  # async 或 sync callable
    enabled: bool = True


class DataSourceChain:
    """数据源优先级链管理器"""

    # 指数退避最大冷却时间 (秒)
    MAX_COOLDOWN = 300

    def __init__(self):
        self._chains: Dict[str, List[DataSource]] = {}
        self._health: Dict[str, _SourceHealth] = {}

    def register(self, category: str, sources: List[DataSource]) -> None:
        """注册某数据类别的优先级链。

        Args:
            category: 如 "symbols:cn_stock", "kline:cn", "realtime:crypto"
            sources: 有序数据源列表 (高优先级在前)
        """
        self._chains[category] = sources
        for src in sources:
            key = f"{category}:{src.name}"
            if key not in self._health:
                self._health[key] = _SourceHealth()
        logger.debug("[DataSourceChain] 注册 %s: %s",
                     category, [s.name for s in sources])

    def fetch(self, category: str, **kwargs) -> Any:
        """按优先级链依次尝试获取数据。

        Returns:
            第一个成功的数据源返回的结果

        Raises:
            AllSourcesFailedError: 所有源均失败
        """
        sources = self._chains.get(category, [])
        if not sources:
            raise AllSourcesFailedError(category, ["未注册任何数据源"])

        errors: List[str] = []

        for src in sources:
            if not src.enabled:
                continue

            health_key = f"{category}:{src.name}"
            health = self._health.get(health_key, _SourceHealth())

            if not self._is_available(health):
                logger.debug("[DataSourceChain] 跳过 %s (冷却中)", src.name)
                continue

            try:
                result = src.fetch(**kwargs)
                self._mark_success(health_key)
                return result
            except Exception as exc:
                err_msg = f"{src.name}: {exc}"
                errors.append(err_msg)
                self._mark_failure(health_key, exc)
                logger.warning("[DataSourceChain] %s 失败: %s, 尝试下一个",
                               src.name, exc)

        raise AllSourcesFailedError(category, errors)

    def get_health_report(self) -> Dict[str, Dict[str, Any]]:
        """返回所有数据源的健康状态 (调试/监控用)"""
        report = {}
        for key, health in self._health.items():
            report[key] = {
                "healthy": health.healthy,
                "fail_count": health.fail_count,
                "permanent_skip": health.permanent_skip,
                "last_error": health.last_error,
            }
        return report

    def reset(self, category: Optional[str] = None) -> None:
        """重置健康状态 (用于配置变更后)"""
        keys_to_reset = []
        for key in self._health:
            if category is None or key.startswith(f"{category}:"):
                keys_to_reset.append(key)
        for key in keys_to_reset:
            self._health[key] = _SourceHealth()

    # ==================== 内部方法 ====================

    def _is_available(self, health: _SourceHealth) -> bool:
        """判断数据源是否可用 (基于指数退避)"""
        if health.permanent_skip:
            return False
        if health.healthy:
            return True
        # 指数退避: 冷却 min(2^fail_count, MAX_COOLDOWN) 秒
        cooldown = min(2 ** health.fail_count, self.MAX_COOLDOWN)
        elapsed = time.monotonic() - health.last_fail_at
        return elapsed >= cooldown

    def _mark_success(self, key: str) -> None:
        health = self._health.setdefault(key, _SourceHealth())
        health.healthy = True
        health.fail_count = 0
        health.last_error = ""

    def _mark_failure(self, key: str, exc: Exception) -> None:
        health = self._health.setdefault(key, _SourceHealth())
        health.healthy = False
        health.fail_count += 1
        health.last_fail_at = time.monotonic()
        health.last_error = str(exc)

        # 权限/认证/配额类错误 → 永久跳过（直到 reset）
        if self._is_permanent_error(exc):
            health.permanent_skip = True
            logger.info("[DataSourceChain] %s 永久跳过 (权限/认证错误)", key)

    @staticmethod
    def _is_permanent_error(exc: Exception) -> bool:
        """判断是否为需永久跳过的错误 (权限/认证/配额)"""
        status_code = getattr(exc, "status_code", None)
        if status_code in (401, 403):
            return True

        code_str = str(getattr(exc, "code", "") or "").upper()
        if code_str in ("PERMISSION_DENIED", "FORBIDDEN", "AUTHENTICATION_FAILED",
                         "INVALID_API_KEY"):
            return True

        msg = str(exc).lower()
        permanent_keywords = ("api key", "authentication", "permission denied",
                              "forbidden", "unauthorized", "invalid key")
        return any(kw in msg for kw in permanent_keywords)
