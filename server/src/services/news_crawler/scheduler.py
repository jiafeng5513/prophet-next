# -*- coding: utf-8 -*-
"""
===================================
新闻采集调度器
===================================

职责：
1. 管理所有爬虫实例
2. 定时触发采集任务
3. 采集后持久化（去重由 repository 负责）
4. 触发 LLM 处理管线
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Dict, List, Optional

from src.services.news_crawler.base_crawler import BaseCrawler
from src.services.news_crawler.models import CrawledNewsItem
from src.services.news_crawler.repository import NewsRepository

logger = logging.getLogger(__name__)


class NewsCrawlScheduler:
    """
    新闻采集调度器 - 单例

    使用方式：
        scheduler = NewsCrawlScheduler.get_instance()
        scheduler.register_crawler(EastMoneyCrawler())
        await scheduler.start()
    """

    _instance: Optional["NewsCrawlScheduler"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "NewsCrawlScheduler":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._crawlers: Dict[str, BaseCrawler] = {}
        self._repo = NewsRepository()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._interval_seconds: int = 300  # 默认 5 分钟
        self._on_new_items_callback = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @interval_seconds.setter
    def interval_seconds(self, value: int):
        self._interval_seconds = max(60, value)  # 最小 60 秒

    def register_crawler(self, crawler: BaseCrawler):
        """注册爬虫"""
        self._crawlers[crawler.source_name] = crawler
        logger.info(f"[NewsScheduler] 注册爬虫: {crawler.source_name}")

    def unregister_crawler(self, source_name: str):
        """注销爬虫"""
        self._crawlers.pop(source_name, None)

    def set_on_new_items(self, callback):
        """
        设置新条目回调（用于触发 LLM 处理）

        callback signature: async def on_new(items: List[CrawledNewsItem]) -> None
        """
        self._on_new_items_callback = callback

    async def start(self):
        """启动定时采集"""
        if self._running:
            logger.warning("[NewsScheduler] 已经在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            f"[NewsScheduler] 启动, 间隔={self._interval_seconds}s, "
            f"爬虫数={len(self._crawlers)}"
        )

    async def stop(self):
        """停止定时采集"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("[NewsScheduler] 已停止")

    async def run_once(self) -> int:
        """手动触发一次采集，返回新增条数"""
        total_new = 0
        all_items: List[CrawledNewsItem] = []

        for name, crawler in self._crawlers.items():
            if not crawler.enabled:
                continue
            try:
                items = await crawler.fetch_news()
                all_items.extend(items)
                logger.debug(f"[NewsScheduler] {name} 采集 {len(items)} 条")
            except Exception as e:
                logger.error(f"[NewsScheduler] {name} 采集失败: {e}")

        if all_items:
            total_new = self._repo.save_batch(all_items)

            # 触发 LLM 处理回调
            if total_new > 0 and self._on_new_items_callback:
                try:
                    await self._on_new_items_callback(all_items[:total_new])
                except Exception as e:
                    logger.error(f"[NewsScheduler] 回调处理失败: {e}")

        return total_new

    async def _loop(self):
        """定时循环"""
        while self._running:
            try:
                count = await self.run_once()
                if count > 0:
                    logger.info(f"[NewsScheduler] 本轮新增 {count} 条")
            except Exception as e:
                logger.error(f"[NewsScheduler] 循环异常: {e}")

            # 等待间隔
            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break

    def get_status(self) -> dict:
        """获取调度器状态"""
        stats = self._repo.count_news(hours=24)
        return {
            "running": self._running,
            "interval_seconds": self._interval_seconds,
            "crawlers": {
                name: {"enabled": c.enabled}
                for name, c in self._crawlers.items()
            },
            "last_24h_stats": stats,
        }
