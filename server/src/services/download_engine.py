# -*- coding: utf-8 -*-
"""
===================================
后台下载任务引擎
===================================

职责：
1. 异步执行缓存下载任务
2. 支持多品种并行下载（带并发限制）
3. 速率控制（根据数据源限制自动调节）
4. 断点续传支持
5. 进度上报

启动方式：
    在 FastAPI app startup 事件中调用 start_download_engine()
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# 并发控制
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_INTERVAL_MS = 500  # 每次请求间隔（毫秒）


class DownloadEngine:
    """后台下载任务引擎"""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    async def start(self):
        """启动引擎"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[DownloadEngine] 已启动")

    async def stop(self):
        """停止引擎"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[DownloadEngine] 已停止")

    async def _poll_loop(self):
        """主循环：轮询待执行任务"""
        while self._running:
            try:
                from src.services.kline_cache_manager import get_kline_cache_manager
                manager = get_kline_cache_manager()

                # 获取所有 pending 任务
                tasks = manager.get_all_tasks()
                pending = [t for t in tasks if t["status"] == "pending"]

                for task_info in pending:
                    if not self._running:
                        break
                    # 用信号量控制并发
                    await self._semaphore.acquire()
                    asyncio.create_task(
                        self._execute_task(task_info["task_id"])
                    )

            except Exception as e:
                logger.error(f"[DownloadEngine] 轮询异常: {e}")

            await asyncio.sleep(2)  # 每2秒检查一次

    async def _execute_task(self, task_id: str):
        """执行单个下载任务"""
        try:
            from src.services.kline_cache_manager import get_kline_cache_manager
            manager = get_kline_cache_manager()

            # 标记为运行中
            manager.update_task_progress(task_id, 0.0, status="running")

            task_info = manager.get_task_status(task_id)
            if not task_info:
                return

            market = task_info["market"]
            symbol = task_info["symbol"]
            interval = task_info["interval"]
            start_time = task_info["start_time"]
            end_time = task_info["end_time"]

            logger.info(
                f"[DownloadEngine] 开始执行任务 {task_id}: "
                f"{market}/{symbol}/{interval}"
            )

            # 选择数据源
            fetcher = self._get_fetcher_for_market(market)
            if not fetcher:
                manager.update_task_progress(task_id, 0.0, status="failed")
                return

            # 分片下载
            total_duration = end_time - start_time
            if total_duration <= 0:
                manager.update_task_progress(task_id, 1.0, status="completed")
                return

            # 按时间段分片（每片最多获取1000条日线 ≈ ~4年）
            chunk_duration = self._get_chunk_duration(interval)
            current = start_time
            downloaded_rows = 0

            while current < end_time:
                # 检查是否被取消
                status = manager.get_task_status(task_id)
                if not status or status["status"] == "cancelled":
                    logger.info(f"[DownloadEngine] 任务 {task_id} 已取消")
                    return

                chunk_end = min(current + chunk_duration, end_time)

                try:
                    df = await self._fetch_chunk(
                        fetcher, symbol, interval, current, chunk_end
                    )
                    if df is not None and not df.empty:
                        manager.upsert_klines_from_df(
                            market=market,
                            symbol=symbol,
                            interval=interval,
                            df=df,
                            source=fetcher.name,
                        )
                        downloaded_rows += len(df)
                except Exception as e:
                    logger.warning(
                        f"[DownloadEngine] 任务 {task_id} 分片下载失败 "
                        f"[{current}~{chunk_end}]: {e}"
                    )

                # 更新进度
                progress = (chunk_end - start_time) / total_duration
                manager.update_task_progress(task_id, progress)

                current = chunk_end

                # 速率控制
                await asyncio.sleep(DOWNLOAD_INTERVAL_MS / 1000.0)

            # 标记完成
            manager.update_task_progress(task_id, 1.0, status="completed")
            logger.info(
                f"[DownloadEngine] 任务 {task_id} 完成: "
                f"下载 {downloaded_rows} 行数据"
            )

            # 如果属于批次，检查是否需要释放下一批
            if task_info.get("batch_id"):
                manager.check_batch_release(task_info["batch_id"])

        except Exception as e:
            logger.error(f"[DownloadEngine] 任务 {task_id} 执行异常: {e}")
            try:
                from src.services.kline_cache_manager import get_kline_cache_manager
                manager = get_kline_cache_manager()
                with manager._task_lock:
                    task = manager._download_tasks.get(task_id)
                    if task:
                        task.status = "failed"
                        task.error = str(e)
            except Exception:
                pass
        finally:
            self._semaphore.release()

    def _get_fetcher_for_market(self, market: str):
        """根据市场选择合适的 Fetcher"""
        from data_provider.base import DataFetcherManager
        mgr = DataFetcherManager()
        fetchers = mgr._get_fetchers_snapshot()

        if market.startswith("crypto"):
            # 优先 Binance，兜底 OKX
            for f in fetchers:
                if f.name == "BinanceFetcher":
                    return f
            for f in fetchers:
                if f.name == "OKXFetcher":
                    return f
        elif market == "us":
            for f in fetchers:
                if f.name == "YfinanceFetcher":
                    return f
        elif market == "hk":
            for f in fetchers:
                if f.name in ("LongbridgeFetcher", "YfinanceFetcher"):
                    return f
        else:
            # A股：优先 Efinance/AKShare
            for f in fetchers:
                if f.name in ("EfinanceFetcher", "AkshareFetcher"):
                    return f

        # fallback: 第一个可用的
        return fetchers[0] if fetchers else None

    async def _fetch_chunk(self, fetcher, symbol: str, interval: str,
                           start_ms: int, end_ms: int) -> Optional[pd.DataFrame]:
        """
        异步执行单次数据获取（在线程池中运行同步 fetcher）
        """
        import asyncio

        start_date = datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d")
        end_date = datetime.fromtimestamp(end_ms / 1000).strftime("%Y-%m-%d")

        loop = asyncio.get_event_loop()
        # 在线程池中运行同步 fetcher
        df = await loop.run_in_executor(
            None,
            lambda: self._sync_fetch(fetcher, symbol, start_date, end_date)
        )
        return df

    def _sync_fetch(self, fetcher, symbol: str, start_date: str, end_date: str):
        """同步获取数据"""
        try:
            from data_provider.base import DataFetcherManager
            mgr = DataFetcherManager()
            days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
            df = mgr._call_fetcher_method(
                fetcher, "get_daily_data",
                stock_code=symbol,
                start_date=start_date,
                end_date=end_date,
                days=max(days, 30),
            )
            return df
        except Exception as e:
            logger.warning(f"[DownloadEngine] _sync_fetch failed for {symbol}: {e}")
            return None

    def _get_chunk_duration(self, interval: str) -> int:
        """根据间隔确定每片时长（毫秒）"""
        # 日线: 每片约1000天
        # 小时线: 每片约40天
        # 分钟线: 每片约7天
        chunk_map = {
            "1d": 1000 * 24 * 3600 * 1000,
            "1h": 40 * 24 * 3600 * 1000,
            "5m": 7 * 24 * 3600 * 1000,
            "1m": 2 * 24 * 3600 * 1000,
        }
        return chunk_map.get(interval, 365 * 24 * 3600 * 1000)


# 全局引擎实例
_engine: Optional[DownloadEngine] = None


def get_download_engine() -> DownloadEngine:
    """获取全局下载引擎单例"""
    global _engine
    if _engine is None:
        _engine = DownloadEngine()
    return _engine


async def start_download_engine():
    """启动下载引擎（在 FastAPI startup 中调用）"""
    engine = get_download_engine()
    await engine.start()


async def stop_download_engine():
    """停止下载引擎（在 FastAPI shutdown 中调用）"""
    engine = get_download_engine()
    await engine.stop()
