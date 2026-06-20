# -*- coding: utf-8 -*-
"""
===================================
自选列表服务 (Watchlist Service)
===================================

职责：
1. 自选标的的增删查改
2. 本地 SQLite 持久化（复用 market_cache.db）
3. 排序支持
"""

import logging
import os
import sqlite3
import time
import threading
from contextlib import contextmanager
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_DB = os.path.join(DEFAULT_CACHE_DIR, "market_cache.db")


class WatchlistService:
    """自选列表服务 - 单例模式"""

    _instance: Optional["WatchlistService"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = DEFAULT_DB):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = DEFAULT_DB):
        if self._initialized:
            return
        self._db_path = db_path
        self._write_lock = threading.Lock()
        self._init_db()
        self._initialized = True

    def _init_db(self):
        """初始化自选表"""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol      TEXT NOT NULL,
                    name        TEXT DEFAULT '',
                    market_type TEXT DEFAULT '',
                    exchange    TEXT DEFAULT '',
                    data_source TEXT DEFAULT '',
                    sort_order  INTEGER DEFAULT 0,
                    added_at    REAL NOT NULL,
                    PRIMARY KEY (symbol)
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_sort
                    ON watchlist(sort_order);
            """)

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有自选标的，按 sort_order 排序"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT symbol, name, market_type, exchange, data_source, sort_order, added_at "
                "FROM watchlist ORDER BY sort_order ASC, added_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def add(self, symbol: str, name: str = "", market_type: str = "",
            exchange: str = "", data_source: str = "") -> bool:
        """添加到自选，返回是否新增"""
        with self._write_lock:
            with self._get_conn() as conn:
                existing = conn.execute(
                    "SELECT symbol FROM watchlist WHERE symbol = ?", (symbol,)
                ).fetchone()
                if existing:
                    return False
                # sort_order = 当前最大值 + 1
                max_order = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) FROM watchlist"
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO watchlist (symbol, name, market_type, exchange, data_source, sort_order, added_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (symbol, name, market_type, exchange, data_source, max_order + 1, time.time())
                )
                logger.info(f"[Watchlist] 添加自选: {symbol} ({name})")
                return True

    def remove(self, symbol: str) -> bool:
        """从自选中移除，返回是否删除了"""
        with self._write_lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM watchlist WHERE symbol = ?", (symbol,)
                )
                if cursor.rowcount > 0:
                    logger.info(f"[Watchlist] 移除自选: {symbol}")
                    return True
                return False

    def contains(self, symbol: str) -> bool:
        """检查是否在自选中"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM watchlist WHERE symbol = ?", (symbol,)
            ).fetchone()
            return row is not None

    def reorder(self, symbols: List[str]) -> None:
        """按传入顺序重排自选列表"""
        with self._write_lock:
            with self._get_conn() as conn:
                for i, symbol in enumerate(symbols):
                    conn.execute(
                        "UPDATE watchlist SET sort_order = ? WHERE symbol = ?",
                        (i, symbol)
                    )

    def clear(self) -> int:
        """清空自选列表，返回删除数量"""
        with self._write_lock:
            with self._get_conn() as conn:
                cursor = conn.execute("DELETE FROM watchlist")
                count = cursor.rowcount
                logger.info(f"[Watchlist] 清空自选: {count} 个")
                return count
