# -*- coding: utf-8 -*-
"""
===================================
TickFlowFetcher - market review only
===================================

Issue #632 only requires TickFlow for A-share market review stability.
This fetcher intentionally implements a narrow P0 surface:

1. Main A-share indices quotes
2. A-share market breadth statistics

It does not participate in the general daily-data or per-stock realtime
pipelines and should only be called explicitly by DataFetcherManager.
"""

import logging
import math
from threading import RLock
from time import monotonic
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import (
    BaseFetcher,
    DataFetchError,
    is_bse_code,
    is_kc_cy_stock,
    is_st_stock,
    normalize_stock_code,
)


logger = logging.getLogger(__name__)

_CN_MAIN_INDEX_QUOTES = (
    ("000001.SH", "000001", "上证指数"),
    ("399001.SZ", "399001", "深证成指"),
    ("399006.SZ", "399006", "创业板指"),
    ("000688.SH", "000688", "科创50"),
    ("000016.SH", "000016", "上证50"),
    ("000300.SH", "000300", "沪深300"),
)
_MAX_SYMBOLS_PER_QUOTE_REQUEST = 5
_UNIVERSE_PERMISSION_NEGATIVE_CACHE_TTL_SECONDS = 900


class TickFlowFetcher(BaseFetcher):
    """TickFlow-backed market review helper."""

    name = "TickFlowFetcher"
    priority = 99

    def __init__(self, api_key: Optional[str], timeout: float = 30.0):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        self._client = None
        self._client_lock = RLock()
        self._universe_query_supported: Optional[bool] = None
        self._universe_query_checked_at: Optional[float] = None
        # 限流退避状态
        self._rate_limit_until: float = 0.0  # monotonic timestamp until which we should not request
        self._rate_limit_logged: bool = False  # 是否已经输出过本轮限流 WARNING
        self._realtime_cache: Dict[str, List[Dict[str, Any]]] = {}  # 缓存最近成功的实时行情结果

    def close(self) -> None:
        """Close the underlying TickFlow client if it was created."""
        with self._client_lock:
            client = self._client
            self._client = None
            self._universe_query_supported = None
            self._universe_query_checked_at = None
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                logger.debug("[TickFlowFetcher] 关闭客户端失败: %s", exc)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            # Best-effort cleanup during interpreter shutdown.
            pass

    def _build_client(self):
        from tickflow import TickFlow

        return TickFlow(api_key=self.api_key, timeout=self.timeout)

    def _get_client(self):
        if not self.api_key:
            return None
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is None:
                self._client = self._build_client()
            return self._client

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        raise DataFetchError(
            "TickFlowFetcher P0 only supports market review endpoints"
        )

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        raise DataFetchError(
            "TickFlowFetcher P0 only supports market review endpoints"
        )

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value in (None, "", "-"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _ratio_to_percent(cls, value: Any) -> Optional[float]:
        ratio = cls._safe_float(value)
        if ratio is None:
            return None
        return ratio * 100.0

    @staticmethod
    def _extract_name(quote: Dict[str, Any]) -> str:
        ext = quote.get("ext") or {}
        name = ext.get("name") or quote.get("name") or ""
        return str(name).strip()

    @staticmethod
    def _is_universe_permission_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        code = str(getattr(exc, "code", "") or "").upper()
        message = (
            f"{getattr(exc, 'message', '')} {exc}"
        ).strip().lower()

        if status_code == 403:
            return True
        if code in {"PERMISSION_DENIED", "FORBIDDEN"}:
            return True
        return any(
            keyword in message
            for keyword in (
                "标的池查询",
                "universe",
                "permission",
                "forbidden",
            )
        )

    @staticmethod
    def _is_cn_equity_symbol(symbol: str) -> bool:
        normalized = normalize_stock_code(symbol)
        upper_symbol = (symbol or "").strip().upper()
        return (
            normalized.isdigit()
            and len(normalized) == 6
            and upper_symbol.endswith((".SH", ".SZ", ".BJ"))
        )

    @staticmethod
    def _round_limit_price(prev_close: float, ratio: float) -> float:
        return math.floor(prev_close * (1 + ratio) * 100 + 0.5) / 100.0

    @classmethod
    def _get_limit_ratio(cls, pure_code: str, name: str) -> float:
        if is_bse_code(pure_code):
            return 0.30
        if is_kc_cy_stock(pure_code):
            return 0.20
        if is_st_stock(name):
            return 0.05
        return 0.10

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """Fetch main A-share indices via TickFlow quotes."""
        if region != "cn":
            return None

        client = self._get_client()
        if client is None:
            return None

        symbols = [symbol for symbol, _, _ in _CN_MAIN_INDEX_QUOTES]
        quotes: List[Dict[str, Any]] = []
        for offset in range(0, len(symbols), _MAX_SYMBOLS_PER_QUOTE_REQUEST):
            batch_symbols = symbols[offset : offset + _MAX_SYMBOLS_PER_QUOTE_REQUEST]
            batch_quotes = client.quotes.get(symbols=batch_symbols)
            if batch_quotes:
                quotes.extend(batch_quotes)
        if not quotes:
            logger.warning("[TickFlowFetcher] 指数行情为空")
            return None

        quotes_by_symbol = {
            str(item.get("symbol", "")).upper(): item for item in quotes if item
        }
        results: List[Dict[str, Any]] = []

        for symbol, code, name in _CN_MAIN_INDEX_QUOTES:
            quote = quotes_by_symbol.get(symbol)
            if not quote:
                continue

            ext = quote.get("ext") or {}
            current = self._safe_float(quote.get("last_price")) or 0.0
            prev_close = self._safe_float(quote.get("prev_close")) or 0.0
            change = self._safe_float(ext.get("change_amount"))
            if change is None:
                change = current - prev_close if current or prev_close else 0.0
            amplitude = self._ratio_to_percent(ext.get("amplitude"))
            if amplitude is None and prev_close > 0:
                high = self._safe_float(quote.get("high")) or 0.0
                low = self._safe_float(quote.get("low")) or 0.0
                amplitude = (high - low) / prev_close * 100

            results.append(
                {
                    "code": code,
                    "name": name,
                    "current": current,
                    "change": change,
                    "change_pct": self._ratio_to_percent(ext.get("change_pct")) or 0.0,
                    "open": self._safe_float(quote.get("open")) or 0.0,
                    "high": self._safe_float(quote.get("high")) or 0.0,
                    "low": self._safe_float(quote.get("low")) or 0.0,
                    "prev_close": prev_close,
                    "volume": self._safe_float(quote.get("volume")) or 0.0,
                    "amount": self._safe_float(quote.get("amount")) or 0.0,
                    "amplitude": amplitude or 0.0,
                }
            )

        if len(results) != len(_CN_MAIN_INDEX_QUOTES):
            logger.warning(
                "[TickFlowFetcher] 指数行情不完整: %s/%s",
                len(results),
                len(_CN_MAIN_INDEX_QUOTES),
            )
            return None

        return results or None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """Calculate A-share market breadth from TickFlow universe quotes."""
        client = self._get_client()
        if client is None:
            return None

        now = monotonic()
        if self._universe_query_supported is False:
            checked_at = self._universe_query_checked_at or 0.0
            if (
                now - checked_at
                < _UNIVERSE_PERMISSION_NEGATIVE_CACHE_TTL_SECONDS
            ):
                return None
            self._universe_query_supported = None
            self._universe_query_checked_at = None

        try:
            quotes = client.quotes.get(universes=["CN_Equity_A"])
            self._universe_query_supported = True
            self._universe_query_checked_at = now
        except Exception as exc:
            if self._is_universe_permission_error(exc):
                self._universe_query_supported = False
                self._universe_query_checked_at = now
                logger.info(
                    "[TickFlowFetcher] 当前套餐不支持标的池查询，市场统计回退到现有数据源"
                )
                return None
            raise
        if not quotes:
            logger.warning("[TickFlowFetcher] 市场统计行情为空")
            return None

        stats = {
            "up_count": 0,
            "down_count": 0,
            "flat_count": 0,
            "limit_up_count": 0,
            "limit_down_count": 0,
            "total_amount": 0.0,
        }
        valid_rows = 0

        for quote in quotes:
            if not quote:
                continue

            symbol = str(quote.get("symbol") or "").strip().upper()
            if not self._is_cn_equity_symbol(symbol):
                continue

            amount = self._safe_float(quote.get("amount"))
            if amount is not None and amount > 0:
                stats["total_amount"] += amount / 1e8

            pure_code = normalize_stock_code(symbol)
            last_price = self._safe_float(quote.get("last_price"))
            prev_close = self._safe_float(quote.get("prev_close"))

            if last_price is None or prev_close is None or amount is None or amount <= 0:
                continue

            name = self._extract_name(quote)
            if not name:
                logger.debug("[TickFlowFetcher] 缺少股票名称，按非 ST 处理: %s", symbol)

            ratio = self._get_limit_ratio(pure_code, name)
            limit_up = self._round_limit_price(prev_close, ratio)
            limit_down = math.floor(prev_close * (1 - ratio) * 100 + 0.5) / 100.0
            limit_up_tolerance = round(abs(prev_close * (1 + ratio) - limit_up), 10)
            limit_down_tolerance = round(
                abs(prev_close * (1 - ratio) - limit_down), 10
            )

            valid_rows += 1

            if abs(last_price - limit_up) <= limit_up_tolerance:
                stats["limit_up_count"] += 1
            if abs(last_price - limit_down) <= limit_down_tolerance:
                stats["limit_down_count"] += 1

            if last_price > prev_close:
                stats["up_count"] += 1
            elif last_price < prev_close:
                stats["down_count"] += 1
            else:
                stats["flat_count"] += 1

        if valid_rows == 0:
            logger.warning("[TickFlowFetcher] 市场统计未命中有效 A 股行情")
            return None

        return stats

    # ================================================================
    # P1 接口 — 标的列表 / K线 / 实时行情 (Phase 6 数据源链)
    # ================================================================

    def get_symbol_list(self, market_type: str) -> List[Dict[str, Any]]:
        """通过 TickFlow Universe 获取标的列表。

        Args:
            market_type: cn_stock / cn_etf / cn_index / us_stock / hk_stock

        Returns:
            统一格式标的列表
        """
        from src.services.tickflow_symbol import UNIVERSE_MAP, from_tickflow_symbol

        universe_id = UNIVERSE_MAP.get(market_type)
        if not universe_id:
            return []

        client = self._get_client()
        if client is None:
            # 无 API Key 时尝试 free 客户端
            client = self._get_free_client()
        if client is None:
            return []

        try:
            universe = client.universes.get(universe_id)
        except Exception as exc:
            if self._is_universe_permission_error(exc):
                logger.info("[TickFlowFetcher] 标的池 %s 权限不足", universe_id)
                return []
            raise

        tf_symbols = universe.get("symbols") or []
        if not tf_symbols:
            return []

        # 批量获取标的元数据
        try:
            instruments = client.instruments.batch(symbols=tf_symbols)
        except Exception:
            # instruments 不可用时，退化为仅代码列表
            instruments = [{"symbol": s} for s in tf_symbols]

        results: List[Dict[str, Any]] = []
        for inst in instruments:
            tf_sym = str(inst.get("symbol", "")).strip()
            if not tf_sym:
                continue
            code = from_tickflow_symbol(tf_sym)
            name = inst.get("name") or inst.get("short_name") or ""
            exchange = inst.get("exchange") or tf_sym.rsplit(".", 1)[-1] if "." in tf_sym else ""

            results.append({
                "symbol": code,
                "name": str(name).strip(),
                "exchange": exchange.upper() if isinstance(exchange, str) else "",
                "data_source": "tickflow",
                "currency": inst.get("currency") or "CNY",
                "status": "trading",
            })

        logger.info("[TickFlowFetcher] 标的列表 %s: %d 条", market_type, len(results))
        return results

    def get_klines(
        self,
        symbol: str,
        period: str = "1d",
        *,
        count: int = 300,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        adjust: str = "forward",
    ) -> List[Dict[str, Any]]:
        """获取 K 线数据 (统一格式)。

        Args:
            symbol: 内部代码 (如 600519)
            period: 内部周期 (如 1d, 5, 60)
            count: 最多返回条数
            start_time: 起始时间 (秒级时间戳, 可选)
            end_time: 结束时间 (秒级时间戳, 可选)
            adjust: 复权类型 forward / backward / none

        Returns:
            [{"time": int, "open": float, ...}, ...]
        """
        from src.services.tickflow_symbol import to_tickflow_symbol, PERIOD_MAP

        tf_symbol = to_tickflow_symbol(symbol)
        tf_period = PERIOD_MAP.get(period, period)

        is_minute = tf_period.endswith("m")
        client = self._get_client() if is_minute else (self._get_client() or self._get_free_client())
        if client is None:
            raise DataFetchError("TickFlow 客户端不可用 (无 API Key)")

        kwargs: Dict[str, Any] = {
            "period": tf_period,
            "adjust": adjust,
        }
        if count:
            kwargs["count"] = min(count, 10000)
        if start_time:
            kwargs["start_time"] = start_time * 1000  # 秒 → 毫秒
        if end_time:
            kwargs["end_time"] = end_time * 1000

        try:
            data = client.klines.get(tf_symbol, **kwargs)
        except Exception as exc:
            raise DataFetchError(f"TickFlow K 线获取失败 ({tf_symbol}): {exc}") from exc

        return self._normalize_klines(data)

    def get_realtime_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """批量获取实时行情 (统一格式)。

        Args:
            symbols: 内部代码列表

        Returns:
            统一格式行情列表
        """
        from src.services.tickflow_symbol import to_tickflow_symbol, from_tickflow_symbol

        client = self._get_client()
        if client is None:
            raise DataFetchError("TickFlow 实时行情需要 API Key")

        # 限流退避：冷却期内直接返回缓存
        now = monotonic()
        cache_key = ",".join(sorted(symbols[:50]))
        if now < self._rate_limit_until:
            cached = self._realtime_cache.get(cache_key)
            if cached:
                return cached
            # 无缓存也不请求，返回空
            return []

        tf_symbols = [to_tickflow_symbol(s) for s in symbols]

        all_quotes: List[Dict[str, Any]] = []
        rate_limited = False
        for offset in range(0, len(tf_symbols), _MAX_SYMBOLS_PER_QUOTE_REQUEST):
            # 如果本轮已被限流，跳过后续批次
            if rate_limited:
                break
            batch = tf_symbols[offset: offset + _MAX_SYMBOLS_PER_QUOTE_REQUEST]
            try:
                quotes = client.quotes.get(symbols=batch)
                if quotes:
                    all_quotes.extend(quotes)
            except Exception as exc:
                exc_msg = str(exc)
                if "限流" in exc_msg or "rate" in exc_msg.lower():
                    rate_limited = True
                    # 解析重试等待时间
                    retry_ms = self._parse_retry_ms(exc_msg)
                    self._rate_limit_until = now + (retry_ms / 1000.0) if retry_ms > 0 else now + 60.0
                    if not self._rate_limit_logged:
                        logger.warning("[TickFlowFetcher] 实时行情限流，%.0f秒后恢复", self._rate_limit_until - now)
                        self._rate_limit_logged = True
                    else:
                        logger.debug("[TickFlowFetcher] 实时行情仍在限流中，%.0f秒后恢复", self._rate_limit_until - now)
                else:
                    logger.warning("[TickFlowFetcher] 实时行情批次失败: %s", exc)

        results: List[Dict[str, Any]] = []
        for q in all_quotes:
            tf_sym = str(q.get("symbol", ""))
            code = from_tickflow_symbol(tf_sym)
            ext = q.get("ext") or {}
            results.append({
                "symbol": code,
                "name": self._extract_name(q),
                "price": self._safe_float(q.get("last_price")),
                "change": self._safe_float(ext.get("change_amount")),
                "change_percent": self._ratio_to_percent(ext.get("change_pct")),
                "volume": self._safe_float(q.get("volume")),
                "turnover": self._safe_float(q.get("amount")),
                "high": self._safe_float(q.get("high")),
                "low": self._safe_float(q.get("low")),
                "open": self._safe_float(q.get("open")),
                "prev_close": self._safe_float(q.get("prev_close")),
                "update_time": q.get("timestamp"),
            })

        if results:
            self._realtime_cache[cache_key] = results
            # 限流恢复后重置标志
            self._rate_limit_logged = False
        elif rate_limited:
            # 被限流且没有新结果，返回缓存
            cached = self._realtime_cache.get(cache_key)
            if cached:
                return cached

        return results

    @staticmethod
    def _parse_retry_ms(msg: str) -> int:
        """从限流异常消息中解析重试等待毫秒数"""
        import re
        match = re.search(r"(\d+)\s*ms", msg)
        if match:
            return int(match.group(1))
        return 0

    # ==================== P1 内部辅助 ====================

    def _get_free_client(self):
        """获取免费版 TickFlow 客户端 (无需 API Key)"""
        try:
            from tickflow import TickFlow
            return TickFlow.free()
        except Exception as exc:
            logger.debug("[TickFlowFetcher] 创建 free 客户端失败: %s", exc)
            return None

    @staticmethod
    def _normalize_klines(data) -> List[Dict[str, Any]]:
        """将 TickFlow 列式 K 线数据转为行式统一格式。

        TickFlow 返回格式:
          {"data": {"timestamp": [...], "open": [...], ...}}
        或 pandas DataFrame
        """
        if data is None:
            return []

        # 如果是 DataFrame (SDK as_dataframe=True)
        if isinstance(data, pd.DataFrame):
            bars = []
            for _, row in data.iterrows():
                ts = row.get("timestamp")
                if ts is None:
                    continue
                bars.append({
                    "time": int(ts) // 1000 if int(ts) > 1e12 else int(ts),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)),
                    "turnover": float(row.get("amount", 0) or row.get("turnover", 0)),
                })
            return bars

        # 字典 / 列式格式
        if isinstance(data, dict):
            inner = data.get("data", data)
            timestamps = inner.get("timestamp", [])
            opens = inner.get("open", [])
            highs = inner.get("high", [])
            lows = inner.get("low", [])
            closes = inner.get("close", [])
            volumes = inner.get("volume", [])
            amounts = inner.get("amount", inner.get("turnover", []))

            n = len(timestamps)
            bars = []
            for i in range(n):
                ts = timestamps[i]
                bars.append({
                    "time": int(ts) // 1000 if int(ts) > 1e12 else int(ts),
                    "open": float(opens[i]) if i < len(opens) else 0.0,
                    "high": float(highs[i]) if i < len(highs) else 0.0,
                    "low": float(lows[i]) if i < len(lows) else 0.0,
                    "close": float(closes[i]) if i < len(closes) else 0.0,
                    "volume": float(volumes[i]) if i < len(volumes) else 0.0,
                    "turnover": float(amounts[i]) if i < len(amounts) else 0.0,
                })
            return bars

        return []

    # ==================== P2: 财务数据 ====================

    def get_financials(
        self,
        symbol: str,
        report_type: str = "metrics",
        *,
        limit: int = 8,
    ) -> Dict[str, Any]:
        """获取财务数据。

        Args:
            symbol: 内部代码 (如 600519, AAPL, HK00700)
            report_type: income | balance | cash_flow | metrics | shares
            limit: 返回最近几期

        Returns:
            {"symbol": str, "type": str, "data": [...]}
        """
        from src.services.tickflow_symbol import to_tickflow_symbol

        tf_symbol = to_tickflow_symbol(symbol)
        client = self._get_client()
        if client is None:
            raise DataFetchError("TickFlow 财务数据需要 API Key (Expert 套餐)")

        method_map = {
            "income": "income",
            "balance": "balance_sheet",
            "balance_sheet": "balance_sheet",
            "cash_flow": "cash_flow",
            "metrics": "metrics",
            "shares": "shares",
        }
        method_name = method_map.get(report_type, "metrics")

        try:
            financials_api = getattr(client, "financials", None)
            if financials_api is None:
                raise DataFetchError("TickFlow SDK 版本不支持 financials API")
            method = getattr(financials_api, method_name, None)
            if method is None:
                raise DataFetchError(f"TickFlow financials 不支持 {report_type}")
            result = method(tf_symbol, limit=limit)
        except DataFetchError:
            raise
        except Exception as exc:
            raise DataFetchError(
                f"TickFlow 财务数据获取失败 ({tf_symbol}/{report_type}): {exc}"
            ) from exc

        # 标准化输出
        records = []
        if isinstance(result, list):
            records = result
        elif isinstance(result, pd.DataFrame):
            records = result.to_dict("records")
        elif isinstance(result, dict):
            records = result.get("data", [result])

        return {
            "symbol": symbol,
            "type": report_type,
            "data": records,
        }
