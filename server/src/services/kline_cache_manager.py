# -*- coding: utf-8 -*-
"""
===================================
K线数据本地缓存管理器
===================================

职责：
1. K线数据的本地SQLite持久化存储
2. 缓存元数据管理（覆盖范围追踪）
3. 缓存缺口分析（识别缺失区间）
4. 后台下载任务管理

设计原则：
- 使用已有 market_cache.db (SQLite WAL模式)
- 读取并发安全，写入串行化
- 支持多市场、多品种、多周期
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
DEFAULT_CACHE_DB = os.path.join(DEFAULT_CACHE_DIR, "market_cache.db")


@dataclass
class CacheSegment:
    """缓存段描述"""
    market: str
    symbol: str
    interval: str
    start_time: int  # Unix毫秒时间戳
    end_time: int
    completeness: float = 1.0  # 0.0~1.0
    record_count: int = 0
    source: str = ""


@dataclass
class CacheGap:
    """缓存缺口描述"""
    start_time: int
    end_time: int


@dataclass
class DownloadTask:
    """下载任务描述"""
    task_id: str
    market: str
    symbol: str
    interval: str
    start_time: int
    end_time: int
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: float = 0.0  # 0.0~1.0
    error: str = ""
    created_at: float = field(default_factory=time.time)
    batch_id: str = ""  # 所属批次ID（为空表示单独任务）


@dataclass
class DownloadBatch:
    """批量下载批次描述"""
    batch_id: str
    market: str
    interval: str
    start_time: int
    end_time: int
    total_symbols: int = 0
    completed_symbols: int = 0
    failed_symbols: int = 0
    status: str = "running"  # running, completed, partial_failed, cancelled
    task_ids: List[str] = field(default_factory=list)
    # 分批释放控制
    all_symbols: List[str] = field(default_factory=list)
    released_count: int = 0  # 已释放到队列的数量
    created_at: float = field(default_factory=time.time)


class KlineCacheManager:
    """
    K线数据本地缓存管理器。

    功能：
    - 缓存K线数据到SQLite
    - 查询缓存并识别缺口
    - 管理后台下载任务
    """

    def __init__(self, db_path: str = DEFAULT_CACHE_DB):
        self._db_path = db_path
        self._write_lock = threading.Lock()
        self._download_tasks: Dict[str, DownloadTask] = {}
        self._task_lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        """初始化K线缓存相关表"""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                -- K线数据主表
                CREATE TABLE IF NOT EXISTS kline_data (
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL DEFAULT 0,
                    amount REAL DEFAULT 0,
                    source TEXT DEFAULT '',
                    is_complete INTEGER DEFAULT 1,
                    created_at INTEGER DEFAULT (strftime('%s','now') * 1000),
                    PRIMARY KEY (market, symbol, interval, timestamp)
                );

                CREATE INDEX IF NOT EXISTS idx_kline_lookup
                    ON kline_data(market, symbol, interval, timestamp);
                CREATE INDEX IF NOT EXISTS idx_kline_market_time
                    ON kline_data(market, interval, timestamp);

                -- 缓存元数据表
                CREATE TABLE IF NOT EXISTS kline_cache_meta (
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    start_time INTEGER NOT NULL,
                    end_time INTEGER NOT NULL,
                    completeness REAL DEFAULT 1.0,
                    record_count INTEGER DEFAULT 0,
                    source TEXT DEFAULT '',
                    updated_at INTEGER DEFAULT (strftime('%s','now') * 1000),
                    PRIMARY KEY (market, symbol, interval, start_time)
                );

                CREATE INDEX IF NOT EXISTS idx_kline_meta_lookup
                    ON kline_cache_meta(market, symbol, interval);
            """)

    @contextmanager
    def _get_conn(self):
        """获取SQLite连接"""
        conn = sqlite3.connect(self._db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==================== 写入操作 ====================

    def upsert_klines(self, market: str, symbol: str, interval: str,
                      klines: List[Dict[str, Any]], source: str = "") -> int:
        """
        批量写入K线数据（INSERT OR REPLACE）。

        Args:
            market: 市场标识，如 'crypto_binance', 'crypto_okx', 'cn', 'us', 'hk'
            symbol: 品种代码
            interval: K线间隔
            klines: K线数据列表，每个元素包含:
                - timestamp: Unix毫秒时间戳
                - open, high, low, close: float
                - volume, amount: float (可选)
                - is_complete: bool (可选, 默认True)
            source: 数据来源标记

        Returns:
            写入的记录数
        """
        if not klines:
            return 0

        with self._write_lock:
            with self._get_conn() as conn:
                rows = [
                    (
                        market, symbol, interval,
                        int(k["timestamp"]),
                        float(k["open"]),
                        float(k["high"]),
                        float(k["low"]),
                        float(k["close"]),
                        float(k.get("volume", 0)),
                        float(k.get("amount", 0)),
                        source,
                        1 if k.get("is_complete", True) else 0,
                    )
                    for k in klines
                ]

                conn.executemany(
                    """INSERT OR REPLACE INTO kline_data
                       (market, symbol, interval, timestamp, open, high, low, close,
                        volume, amount, source, is_complete)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    rows,
                )

                # 更新缓存元数据
                if rows:
                    timestamps = [r[3] for r in rows]
                    min_ts = min(timestamps)
                    max_ts = max(timestamps)
                    self._update_meta(conn, market, symbol, interval,
                                     min_ts, max_ts, len(rows), source)

                return len(rows)

    def upsert_klines_from_df(self, market: str, symbol: str, interval: str,
                              df: pd.DataFrame, source: str = "") -> int:
        """
        从DataFrame批量写入K线数据。

        DataFrame应包含标准化列: date, open, high, low, close, volume, amount
        """
        if df is None or df.empty:
            return 0

        klines = []
        for _, row in df.iterrows():
            ts = row.get("date")
            if isinstance(ts, pd.Timestamp):
                ts = int(ts.timestamp() * 1000)
            elif isinstance(ts, (int, float)):
                ts = int(ts)
            else:
                continue

            klines.append({
                "timestamp": ts,
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": float(row.get("volume", 0) or 0),
                "amount": float(row.get("amount", 0) or 0),
                "is_complete": True,
            })

        return self.upsert_klines(market, symbol, interval, klines, source)

    def _update_meta(self, conn, market: str, symbol: str, interval: str,
                     start_time: int, end_time: int, count: int, source: str):
        """更新缓存元数据（在写入事务内调用）"""
        now = int(time.time() * 1000)

        # 查找是否有可合并的meta段
        existing = conn.execute(
            """SELECT rowid, start_time, end_time, record_count
               FROM kline_cache_meta
               WHERE market = ? AND symbol = ? AND interval = ?
               AND start_time <= ? AND end_time >= ?
               ORDER BY start_time""",
            (market, symbol, interval, end_time, start_time),
        ).fetchall()

        if existing:
            # 合并: 扩展已有段
            merged_start = min(start_time, min(r["start_time"] for r in existing))
            merged_end = max(end_time, max(r["end_time"] for r in existing))
            total_count = count + sum(r["record_count"] for r in existing)

            # 删除旧段
            rowids = [r["rowid"] for r in existing]
            placeholders = ",".join("?" * len(rowids))
            conn.execute(
                f"DELETE FROM kline_cache_meta WHERE rowid IN ({placeholders})",
                rowids,
            )

            # 插入合并后的段
            conn.execute(
                """INSERT OR REPLACE INTO kline_cache_meta
                   (market, symbol, interval, start_time, end_time,
                    completeness, record_count, source, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (market, symbol, interval, merged_start, merged_end,
                 1.0, total_count, source, now),
            )
        else:
            # 查找相邻的段（前后间隔在一个interval内可合并）
            conn.execute(
                """INSERT OR REPLACE INTO kline_cache_meta
                   (market, symbol, interval, start_time, end_time,
                    completeness, record_count, source, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (market, symbol, interval, start_time, end_time,
                 1.0, count, source, now),
            )

    # ==================== 查询操作 ====================

    def query_klines(self, market: str, symbol: str, interval: str,
                     start_time: int, end_time: int) -> pd.DataFrame:
        """
        查询缓存的K线数据。

        Args:
            market: 市场标识
            symbol: 品种代码
            interval: K线间隔
            start_time: 起始时间（Unix毫秒）
            end_time: 结束时间（Unix毫秒）

        Returns:
            标准化DataFrame (date, open, high, low, close, volume, amount)
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT timestamp, open, high, low, close, volume, amount, is_complete
                   FROM kline_data
                   WHERE market = ? AND symbol = ? AND interval = ?
                   AND timestamp >= ? AND timestamp <= ?
                   ORDER BY timestamp ASC""",
                (market, symbol, interval, start_time, end_time),
            ).fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(r) for r in rows])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop(columns=["timestamp"])
        return df

    def get_cached_range(self, market: str, symbol: str,
                         interval: str) -> Optional[Tuple[int, int]]:
        """获取某品种的已缓存时间范围 (min_timestamp, max_timestamp)"""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT MIN(start_time) as min_ts, MAX(end_time) as max_ts
                   FROM kline_cache_meta
                   WHERE market = ? AND symbol = ? AND interval = ?""",
                (market, symbol, interval),
            ).fetchone()

        if row and row["min_ts"] is not None:
            return (row["min_ts"], row["max_ts"])
        return None

    def find_gaps(self, market: str, symbol: str, interval: str,
                  start_time: int, end_time: int) -> List[CacheGap]:
        """
        查找指定范围内的缓存缺口。

        Returns:
            缺口列表，每个缺口包含 (start_time, end_time)
        """
        with self._get_conn() as conn:
            segments = conn.execute(
                """SELECT start_time, end_time
                   FROM kline_cache_meta
                   WHERE market = ? AND symbol = ? AND interval = ?
                   AND end_time >= ? AND start_time <= ?
                   ORDER BY start_time ASC""",
                (market, symbol, interval, start_time, end_time),
            ).fetchall()

        if not segments:
            return [CacheGap(start_time=start_time, end_time=end_time)]

        gaps = []
        current_start = start_time

        for seg in segments:
            seg_start = max(seg["start_time"], start_time)
            seg_end = min(seg["end_time"], end_time)

            if seg_start > current_start:
                gaps.append(CacheGap(start_time=current_start, end_time=seg_start - 1))
            current_start = max(current_start, seg_end + 1)

        if current_start <= end_time:
            gaps.append(CacheGap(start_time=current_start, end_time=end_time))

        return gaps

    def has_complete_coverage(self, market: str, symbol: str, interval: str,
                             start_time: int, end_time: int) -> bool:
        """检查指定范围是否完全被缓存覆盖"""
        gaps = self.find_gaps(market, symbol, interval, start_time, end_time)
        return len(gaps) == 0

    # ==================== 删除操作 ====================

    def delete_range(self, market: str, symbol: str, interval: str,
                     start_time: int, end_time: int) -> int:
        """
        删除指定范围的缓存数据。

        Returns:
            删除的记录数
        """
        with self._write_lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """DELETE FROM kline_data
                       WHERE market = ? AND symbol = ? AND interval = ?
                       AND timestamp >= ? AND timestamp <= ?""",
                    (market, symbol, interval, start_time, end_time),
                )
                deleted = cursor.rowcount

                # 更新meta：删除完全在范围内的段
                conn.execute(
                    """DELETE FROM kline_cache_meta
                       WHERE market = ? AND symbol = ? AND interval = ?
                       AND start_time >= ? AND end_time <= ?""",
                    (market, symbol, interval, start_time, end_time),
                )

                # 收缩部分重叠的段
                # 段的左部被删除: 收缩start_time
                conn.execute(
                    """UPDATE kline_cache_meta
                       SET start_time = ?
                       WHERE market = ? AND symbol = ? AND interval = ?
                       AND start_time >= ? AND start_time <= ? AND end_time > ?""",
                    (end_time + 1, market, symbol, interval,
                     start_time, end_time, end_time),
                )
                # 段的右部被删除: 收缩end_time
                conn.execute(
                    """UPDATE kline_cache_meta
                       SET end_time = ?
                       WHERE market = ? AND symbol = ? AND interval = ?
                       AND end_time >= ? AND end_time <= ? AND start_time < ?""",
                    (start_time - 1, market, symbol, interval,
                     start_time, end_time, start_time),
                )

                return deleted

    def clear_market(self, market: str) -> int:
        """清空指定市场的所有缓存"""
        with self._write_lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM kline_data WHERE market = ?", (market,)
                )
                conn.execute(
                    "DELETE FROM kline_cache_meta WHERE market = ?", (market,)
                )
                return cursor.rowcount

    def clear_all(self) -> int:
        """清空所有缓存数据"""
        with self._write_lock:
            with self._get_conn() as conn:
                cursor = conn.execute("DELETE FROM kline_data")
                conn.execute("DELETE FROM kline_cache_meta")
                return cursor.rowcount

    # ==================== 状态查询 ====================

    def get_cache_status(self) -> Dict[str, Any]:
        """
        获取缓存整体状态概览。

        Returns:
            {
                "total_records": int,
                "total_size_bytes": int,
                "markets": {
                    "crypto_binance": {"records": ..., "symbols": ..., ...},
                    ...
                }
            }
        """
        with self._get_conn() as conn:
            # 总记录数
            total = conn.execute("SELECT COUNT(*) as cnt FROM kline_data").fetchone()
            total_records = total["cnt"] if total else 0

            # 按市场统计
            market_stats = conn.execute(
                """SELECT market,
                          COUNT(*) as records,
                          COUNT(DISTINCT symbol) as symbols,
                          MIN(timestamp) as earliest,
                          MAX(timestamp) as latest
                   FROM kline_data
                   GROUP BY market"""
            ).fetchall()

        # 获取文件大小
        try:
            db_size = os.path.getsize(self._db_path)
        except OSError:
            db_size = 0

        markets = {}
        for row in market_stats:
            markets[row["market"]] = {
                "records": row["records"],
                "symbols": row["symbols"],
                "earliest": row["earliest"],
                "latest": row["latest"],
            }

        return {
            "total_records": total_records,
            "total_size_bytes": db_size,
            "markets": markets,
        }

    def get_timeline_data(self, market: Optional[str] = None,
                          interval: str = "1d") -> List[Dict[str, Any]]:
        """
        获取时间轴展示数据。

        Returns:
            每个市场的缓存段列表，用于前端时间轴渲染。
        """
        with self._get_conn() as conn:
            if market:
                segments = conn.execute(
                    """SELECT market, symbol, interval, start_time, end_time,
                              completeness, record_count, source
                       FROM kline_cache_meta
                       WHERE market = ? AND interval = ?
                       ORDER BY market, start_time""",
                    (market, interval),
                ).fetchall()
            else:
                segments = conn.execute(
                    """SELECT market, symbol, interval, start_time, end_time,
                              completeness, record_count, source
                       FROM kline_cache_meta
                       WHERE interval = ?
                       ORDER BY market, start_time""",
                    (interval,),
                ).fetchall()

        result = []
        for seg in segments:
            result.append({
                "market": seg["market"],
                "symbol": seg["symbol"],
                "interval": seg["interval"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "completeness": seg["completeness"],
                "record_count": seg["record_count"],
                "source": seg["source"],
            })
        return result

    def get_market_timeline_summary(self, interval: str = "1d") -> Dict[str, List[Dict]]:
        """
        获取按市场分组的时间轴摘要（用于前端多轨道渲染）。
        会将同一市场中重叠/相邻的时间段合并为连续段。

        Returns:
            {
                "crypto_binance": [{"start_time": ..., "end_time": ..., "completeness": ..., "record_count": ...}, ...],
                ...
            }
        """
        with self._get_conn() as conn:
            segments = conn.execute(
                """SELECT market, MIN(start_time) as start_time, MAX(end_time) as end_time,
                          AVG(completeness) as completeness,
                          SUM(record_count) as total_records,
                          COUNT(DISTINCT symbol) as symbol_count
                   FROM kline_cache_meta
                   WHERE interval = ?
                   GROUP BY market, symbol
                   ORDER BY market, start_time""",
                (interval,),
            ).fetchall()

        # 按市场分组
        market_segments: Dict[str, List[Dict]] = {}
        for seg in segments:
            market = seg["market"]
            if market not in market_segments:
                market_segments[market] = []
            market_segments[market].append({
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "completeness": seg["completeness"],
                "record_count": seg["total_records"],
            })

        # 合并每个市场中重叠/相邻的段
        result: Dict[str, List[Dict]] = {}
        for market, segs in market_segments.items():
            segs.sort(key=lambda s: s["start_time"])
            merged = []
            for seg in segs:
                if merged and seg["start_time"] <= merged[-1]["end_time"]:
                    # 与上一段重叠/相邻，合并
                    last = merged[-1]
                    last["end_time"] = max(last["end_time"], seg["end_time"])
                    last["record_count"] += seg["record_count"]
                    last["completeness"] = (last["completeness"] + seg["completeness"]) / 2
                else:
                    merged.append(dict(seg))
            result[market] = merged

        return result

    # ==================== 下载任务管理 ====================

    def create_download_task(self, market: str, symbol: str, interval: str,
                            start_time: int, end_time: int) -> str:
        """
        创建下载任务。

        Returns:
            任务ID
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]

        task = DownloadTask(
            task_id=task_id,
            market=market,
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )

        with self._task_lock:
            self._download_tasks[task_id] = task

        logger.info(
            f"[CacheManager] 创建下载任务 {task_id}: "
            f"{market}/{symbol}/{interval} [{start_time} ~ {end_time}]"
        )
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取下载任务状态"""
        with self._task_lock:
            task = self._download_tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task.task_id,
                "market": task.market,
                "symbol": task.symbol,
                "interval": task.interval,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
                "batch_id": task.batch_id,
            }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有下载任务"""
        with self._task_lock:
            return [
                {
                    "task_id": t.task_id,
                    "market": t.market,
                    "symbol": t.symbol,
                    "interval": t.interval,
                    "status": t.status,
                    "progress": t.progress,
                    "error": t.error,
                }
                for t in self._download_tasks.values()
            ]

    def update_task_progress(self, task_id: str, progress: float,
                            status: Optional[str] = None):
        """更新任务进度"""
        with self._task_lock:
            task = self._download_tasks.get(task_id)
            if task:
                task.progress = min(1.0, max(0.0, progress))
                if status:
                    task.status = status

    def cancel_task(self, task_id: str) -> bool:
        """取消下载任务"""
        with self._task_lock:
            task = self._download_tasks.get(task_id)
            if task and task.status in ("pending", "running"):
                task.status = "cancelled"
                return True
            return False

    # ==================== 批量下载管理 ====================

    def __init_batch_store(self):
        """确保批次存储已初始化"""
        if not hasattr(self, "_download_batches"):
            self._download_batches: Dict[str, DownloadBatch] = {}

    def create_batch_download(self, market: str, interval: str,
                             start_time: int, end_time: int,
                             symbols: List[str]) -> str:
        """
        创建批量下载批次。

        采用分批释放策略：先只创建前 BATCH_RELEASE_SIZE 个子任务，
        完成后再释放下一批。

        Args:
            market: 市场标识
            interval: K线间隔
            start_time: 起始时间（Unix毫秒）
            end_time: 结束时间（Unix毫秒）
            symbols: 品种代码列表

        Returns:
            batch_id
        """
        import uuid
        self.__init_batch_store()

        batch_id = f"batch_{str(uuid.uuid4())[:8]}"

        batch = DownloadBatch(
            batch_id=batch_id,
            market=market,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            total_symbols=len(symbols),
            all_symbols=list(symbols),
            released_count=0,
        )

        with self._task_lock:
            self._download_batches[batch_id] = batch

        # 释放第一批子任务
        self._release_next_batch_chunk(batch_id)

        logger.info(
            f"[CacheManager] 创建批量下载 {batch_id}: "
            f"{market}/{interval} [{len(symbols)} 品种]"
        )
        return batch_id

    def _release_next_batch_chunk(self, batch_id: str, chunk_size: int = 50):
        """释放下一批子任务到队列"""
        self.__init_batch_store()
        with self._task_lock:
            batch = self._download_batches.get(batch_id)
            if not batch or batch.status == "cancelled":
                return

            start_idx = batch.released_count
            end_idx = min(start_idx + chunk_size, len(batch.all_symbols))

            if start_idx >= len(batch.all_symbols):
                return  # 已全部释放

            for i in range(start_idx, end_idx):
                symbol = batch.all_symbols[i]
                task_id = self._create_task_internal(
                    market=batch.market,
                    symbol=symbol,
                    interval=batch.interval,
                    start_time=batch.start_time,
                    end_time=batch.end_time,
                    batch_id=batch_id,
                )
                batch.task_ids.append(task_id)

            batch.released_count = end_idx

    def _create_task_internal(self, market: str, symbol: str, interval: str,
                             start_time: int, end_time: int,
                             batch_id: str = "") -> str:
        """内部创建任务（不加锁，由调用者负责）"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        task = DownloadTask(
            task_id=task_id,
            market=market,
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            batch_id=batch_id,
        )
        self._download_tasks[task_id] = task
        return task_id

    def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批次下载进度"""
        self.__init_batch_store()
        with self._task_lock:
            batch = self._download_batches.get(batch_id)
            if not batch:
                return None

            # 统计子任务状态
            completed = 0
            failed = 0
            running_tasks = []

            for tid in batch.task_ids:
                task = self._download_tasks.get(tid)
                if not task:
                    continue
                if task.status == "completed":
                    completed += 1
                elif task.status == "failed":
                    failed += 1
                elif task.status == "running":
                    running_tasks.append({
                        "task_id": tid,
                        "symbol": task.symbol,
                        "progress": task.progress,
                    })

            batch.completed_symbols = completed
            batch.failed_symbols = failed

            # 计算总体进度
            released = batch.released_count
            total = batch.total_symbols
            if total == 0:
                overall_progress = 1.0
            else:
                # 进度 = (已完成 + 已失败) / 总数
                overall_progress = (completed + failed) / total

            # 判断批次状态
            if batch.status != "cancelled":
                if completed + failed >= total:
                    batch.status = "completed" if failed == 0 else "partial_failed"
                else:
                    batch.status = "running"

            return {
                "batch_id": batch_id,
                "market": batch.market,
                "interval": batch.interval,
                "total_symbols": total,
                "completed_symbols": completed,
                "failed_symbols": failed,
                "overall_progress": round(overall_progress, 4),
                "status": batch.status,
                "current_tasks": running_tasks[:5],  # 最多返回5个当前任务
            }

    def check_batch_release(self, batch_id: str):
        """
        检查是否需要释放下一批子任务。
        由 DownloadEngine 在每个子任务完成后调用。
        """
        self.__init_batch_store()
        with self._task_lock:
            batch = self._download_batches.get(batch_id)
            if not batch or batch.status == "cancelled":
                return

            # 统计当前 pending + running 的任务数
            active_count = sum(
                1 for tid in batch.task_ids
                if self._download_tasks.get(tid)
                and self._download_tasks[tid].status in ("pending", "running")
            )

            # 如果活跃任务少于阈值且还有未释放的品种，释放下一批
            if active_count < 10 and batch.released_count < len(batch.all_symbols):
                # 临时释放锁来调用释放方法（因为它也需要锁）
                pass

        # 在锁外检查并释放
        batch = self._download_batches.get(batch_id)
        if batch and batch.status != "cancelled" and batch.released_count < len(batch.all_symbols):
            # 检查活跃数
            active_count = sum(
                1 for tid in batch.task_ids
                if self._download_tasks.get(tid)
                and self._download_tasks[tid].status in ("pending", "running")
            )
            if active_count < 10:
                self._release_next_batch_chunk(batch_id)

    def cancel_batch(self, batch_id: str) -> bool:
        """取消整个批次的下载任务"""
        self.__init_batch_store()
        with self._task_lock:
            batch = self._download_batches.get(batch_id)
            if not batch:
                return False

            batch.status = "cancelled"
            # 取消所有子任务
            cancelled_count = 0
            for tid in batch.task_ids:
                task = self._download_tasks.get(tid)
                if task and task.status in ("pending", "running"):
                    task.status = "cancelled"
                    cancelled_count += 1

            logger.info(
                f"[CacheManager] 取消批次 {batch_id}: "
                f"取消了 {cancelled_count} 个子任务"
            )
            return True

    def get_all_batches(self) -> List[Dict[str, Any]]:
        """获取所有批次状态（用于前端展示）"""
        self.__init_batch_store()
        results = []
        with self._task_lock:
            for batch_id in self._download_batches:
                pass  # 需要在锁外调用 get_batch_progress

        for batch_id in list(self._download_batches.keys()):
            progress = self.get_batch_progress(batch_id)
            if progress:
                results.append(progress)
        return results


# 全局单例
_cache_manager_instance: Optional[KlineCacheManager] = None
_cache_manager_lock = threading.Lock()


def get_kline_cache_manager(db_path: str = DEFAULT_CACHE_DB) -> KlineCacheManager:
    """获取全局KlineCacheManager单例"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        with _cache_manager_lock:
            if _cache_manager_instance is None:
                _cache_manager_instance = KlineCacheManager(db_path)
    return _cache_manager_instance
