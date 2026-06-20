# -*- coding: utf-8 -*-
"""
===================================
市场数据缓存层
===================================

职责：
1. 标的列表缓存 (SQLite)
2. K 线数据缓存 (SQLite)
3. 缓存 TTL 管理与自动刷新

设计原则：
- 标的列表: TTL 24h, 启动时可预加载
- K 线日线: 增量更新, 无过期
- 写入操作串行化, 读取并发安全
"""

import json
import logging
import os
import sqlite3
import time
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any

try:
    from pypinyin import lazy_pinyin, Style
    _HAS_PINYIN = True
except ImportError:
    _HAS_PINYIN = False


def _name_to_pinyin_short(name: str) -> str:
    """将中文名称转为拼音首字母缩写, 如 '贵州茅台' -> 'gzmt'"""
    if not _HAS_PINYIN or not name:
        return ""
    try:
        initials = lazy_pinyin(name, style=Style.FIRST_LETTER)
        return "".join(initials).lower()
    except Exception:
        return ""

logger = logging.getLogger(__name__)

# 默认缓存数据库路径
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_CACHE_DB = os.path.join(DEFAULT_CACHE_DIR, "market_cache.db")

# 缓存 TTL 配置 (秒)
SYMBOL_LIST_TTL = 24 * 3600     # 标的列表: 24 小时
KLINE_DAILY_TTL = 0             # 日 K 线: 不过期 (增量更新)
KLINE_MINUTE_TTL = 5 * 60       # 分钟 K 线: 5 分钟


class MarketCache:
    """
    市场数据本地 SQLite 缓存

    线程安全: 使用 threading.Lock 串行化写入
    """

    def __init__(self, db_path: str = DEFAULT_CACHE_DB):
        self._db_path = db_path
        self._write_lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS symbol_cache (
                    market_type TEXT NOT NULL,
                    symbol      TEXT NOT NULL,
                    name        TEXT DEFAULT '',
                    exchange    TEXT DEFAULT '',
                    data_source TEXT DEFAULT '',
                    currency    TEXT DEFAULT '',
                    status      TEXT DEFAULT 'trading',
                    extra_json  TEXT DEFAULT '{}',
                    pinyin_short TEXT DEFAULT '',
                    updated_at  REAL NOT NULL,
                    PRIMARY KEY (market_type, symbol)
                );

                CREATE INDEX IF NOT EXISTS idx_symbol_cache_market
                    ON symbol_cache(market_type);

                CREATE TABLE IF NOT EXISTS cache_meta (
                    cache_key   TEXT PRIMARY KEY,
                    updated_at  REAL NOT NULL,
                    ttl         REAL NOT NULL DEFAULT 0,
                    extra       TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS kline_cache (
                    symbol      TEXT NOT NULL,
                    period      TEXT NOT NULL,
                    time        INTEGER NOT NULL,
                    open        REAL NOT NULL,
                    high        REAL NOT NULL,
                    low         REAL NOT NULL,
                    close       REAL NOT NULL,
                    volume      REAL DEFAULT 0,
                    turnover    REAL DEFAULT 0,
                    PRIMARY KEY (symbol, period, time)
                );

                CREATE INDEX IF NOT EXISTS idx_kline_symbol_period
                    ON kline_cache(symbol, period);
            """)

            # 迁移：为已有数据库添加 pinyin_short 列
            try:
                conn.execute("SELECT pinyin_short FROM symbol_cache LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("[MarketCache] 迁移: 添加 pinyin_short 列")
                conn.execute("ALTER TABLE symbol_cache ADD COLUMN pinyin_short TEXT DEFAULT ''")
                conn.commit()

            # 填充空的 pinyin_short (对已有数据)
            if _HAS_PINYIN:
                rows = conn.execute(
                    "SELECT market_type, symbol, name FROM symbol_cache WHERE pinyin_short = '' OR pinyin_short IS NULL"
                ).fetchall()
                if rows:
                    logger.info(f"[MarketCache] 迁移: 为 {len(rows)} 条记录生成拼音索引")
                    for r in rows:
                        py = _name_to_pinyin_short(r[2])
                        if py:
                            conn.execute(
                                "UPDATE symbol_cache SET pinyin_short = ? WHERE market_type = ? AND symbol = ?",
                                (py, r[0], r[1]),
                            )
                    conn.commit()

    @contextmanager
    def _get_conn(self):
        """获取 SQLite 连接 (上下文管理器)"""
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

    # ==================== 标的列表缓存 ====================

    def is_symbol_cache_valid(self, market_type: str) -> bool:
        """检查指定市场类型的标的列表缓存是否有效"""
        cache_key = f"symbols:{market_type}"
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT updated_at, ttl FROM cache_meta WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None:
                return False
            elapsed = time.time() - row["updated_at"]
            ttl = row["ttl"] if row["ttl"] > 0 else SYMBOL_LIST_TTL
            return elapsed < ttl

    def get_cached_symbols(self, market_type: str) -> List[Dict[str, Any]]:
        """获取缓存的标的列表"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM symbol_cache WHERE market_type = ? ORDER BY symbol",
                (market_type,),
            ).fetchall()
            return [dict(r) for r in rows]

    def set_cached_symbols(
        self,
        market_type: str,
        symbols: List[Dict[str, Any]],
        ttl: float = SYMBOL_LIST_TTL,
    ):
        """更新标的列表缓存 (全量替换)"""
        now = time.time()
        with self._write_lock:
            with self._get_conn() as conn:
                # 删除旧数据
                conn.execute(
                    "DELETE FROM symbol_cache WHERE market_type = ?",
                    (market_type,),
                )
                # 批量插入
                if symbols:
                    conn.executemany(
                        """INSERT OR REPLACE INTO symbol_cache
                           (market_type, symbol, name, exchange, data_source, currency, status, extra_json, pinyin_short, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            (
                                market_type,
                                s.get("symbol", ""),
                                s.get("name", ""),
                                s.get("exchange", ""),
                                s.get("data_source", ""),
                                s.get("currency", ""),
                                s.get("status", "trading"),
                                json.dumps(s.get("extra", {}), ensure_ascii=False),
                                _name_to_pinyin_short(s.get("name", "")),
                                now,
                            )
                            for s in symbols
                        ],
                    )
                # 更新元数据
                conn.execute(
                    """INSERT OR REPLACE INTO cache_meta (cache_key, updated_at, ttl)
                       VALUES (?, ?, ?)""",
                    (f"symbols:{market_type}", now, ttl),
                )
        logger.info(f"[MarketCache] 已缓存 {market_type} 标的 {len(symbols)} 条")

    def search_cached_symbols(self, query: str, market_type: str = "") -> List[Dict[str, Any]]:
        """在缓存中搜索标的 (代码、名称、拼音首字母模糊匹配)"""
        like_pattern = f"%{query}%"
        # 同时搜索拼音首字母列
        pinyin_pattern = f"%{query.lower()}%"
        with self._get_conn() as conn:
            if market_type:
                rows = conn.execute(
                    """SELECT * FROM symbol_cache
                       WHERE market_type = ? AND (
                           symbol LIKE ? OR name LIKE ? OR pinyin_short LIKE ?
                       )
                       ORDER BY symbol LIMIT 100""",
                    (market_type, like_pattern, like_pattern, pinyin_pattern),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM symbol_cache
                       WHERE symbol LIKE ? OR name LIKE ? OR pinyin_short LIKE ?
                       ORDER BY symbol LIMIT 100""",
                    (like_pattern, like_pattern, pinyin_pattern),
                ).fetchall()
            return [dict(r) for r in rows]

    # ==================== K 线数据缓存 ====================

    def get_cached_kline(
        self,
        symbol: str,
        period: str,
        start_time: int = 0,
        end_time: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取缓存的 K 线数据"""
        with self._get_conn() as conn:
            if start_time > 0 and end_time > 0:
                rows = conn.execute(
                    """SELECT * FROM kline_cache
                       WHERE symbol = ? AND period = ? AND time >= ? AND time <= ?
                       ORDER BY time""",
                    (symbol, period, start_time, end_time),
                ).fetchall()
            elif start_time > 0:
                rows = conn.execute(
                    """SELECT * FROM kline_cache
                       WHERE symbol = ? AND period = ? AND time >= ?
                       ORDER BY time""",
                    (symbol, period, start_time),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM kline_cache
                       WHERE symbol = ? AND period = ?
                       ORDER BY time""",
                    (symbol, period),
                ).fetchall()
            return [dict(r) for r in rows]

    def set_cached_kline(
        self,
        symbol: str,
        period: str,
        bars: List[Dict[str, Any]],
    ):
        """写入 K 线数据缓存 (增量 upsert)"""
        if not bars:
            return
        with self._write_lock:
            with self._get_conn() as conn:
                conn.executemany(
                    """INSERT OR REPLACE INTO kline_cache
                       (symbol, period, time, open, high, low, close, volume, turnover)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            symbol,
                            period,
                            b["time"],
                            b["open"],
                            b["high"],
                            b["low"],
                            b["close"],
                            b.get("volume", 0),
                            b.get("turnover", 0),
                        )
                        for b in bars
                    ],
                )
        logger.debug(f"[MarketCache] 缓存 K 线 {symbol}/{period} {len(bars)} 条")

    def get_latest_kline_time(self, symbol: str, period: str) -> Optional[int]:
        """获取缓存中最新的 K 线时间戳"""
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT MAX(time) as max_time FROM kline_cache
                   WHERE symbol = ? AND period = ?""",
                (symbol, period),
            ).fetchone()
            if row and row["max_time"]:
                return int(row["max_time"])
            return None

    # ==================== 管理 ====================

    def clear_market_cache(self, market_type: str = ""):
        """清除缓存"""
        with self._write_lock:
            with self._get_conn() as conn:
                if market_type:
                    conn.execute(
                        "DELETE FROM symbol_cache WHERE market_type = ?",
                        (market_type,),
                    )
                    conn.execute(
                        "DELETE FROM cache_meta WHERE cache_key = ?",
                        (f"symbols:{market_type}",),
                    )
                else:
                    conn.execute("DELETE FROM symbol_cache")
                    conn.execute("DELETE FROM cache_meta")
                    conn.execute("DELETE FROM kline_cache")
        logger.info(f"[MarketCache] 已清除缓存: {market_type or 'ALL'}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._get_conn() as conn:
            symbol_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM symbol_cache"
            ).fetchone()["cnt"]
            kline_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM kline_cache"
            ).fetchone()["cnt"]
            meta_rows = conn.execute("SELECT * FROM cache_meta").fetchall()
            meta = {r["cache_key"]: {"updated_at": r["updated_at"], "ttl": r["ttl"]} for r in meta_rows}
        return {
            "symbol_count": symbol_count,
            "kline_count": kline_count,
            "cache_meta": meta,
            "db_path": self._db_path,
        }
