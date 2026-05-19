# -*- coding: utf-8 -*-
"""
===================================
新闻数据存储层 (Repository)
===================================

基于 SQLite 的新闻持久化，复用 market_cache.db。
负责去重、写入、查询。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from src.services.news_crawler.models import CrawledNewsItem
from src.enums import NewsImportance, NewsSentimentLabel

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
DEFAULT_DB = os.path.join(DEFAULT_CACHE_DIR, "market_cache.db")


class NewsRepository:
    """新闻数据持久化层 - 单例"""

    _instance: Optional["NewsRepository"] = None
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
        """建表"""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS crawled_news (
                    id          TEXT PRIMARY KEY,
                    source      TEXT NOT NULL,
                    source_url  TEXT NOT NULL DEFAULT '',
                    author      TEXT,
                    title       TEXT NOT NULL DEFAULT '',
                    content     TEXT NOT NULL DEFAULT '',
                    publish_time TEXT,
                    crawl_time  TEXT NOT NULL,
                    symbols     TEXT DEFAULT '[]',
                    markets     TEXT DEFAULT '[]',
                    tags        TEXT DEFAULT '[]',
                    summary     TEXT,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    importance  TEXT,
                    language    TEXT DEFAULT 'zh',
                    is_processed INTEGER DEFAULT 0,
                    dedupe_key  TEXT NOT NULL,
                    UNIQUE(dedupe_key)
                );

                CREATE INDEX IF NOT EXISTS idx_crawled_news_publish
                    ON crawled_news(publish_time DESC);
                CREATE INDEX IF NOT EXISTS idx_crawled_news_source
                    ON crawled_news(source);
                CREATE INDEX IF NOT EXISTS idx_crawled_news_processed
                    ON crawled_news(is_processed);
                CREATE INDEX IF NOT EXISTS idx_crawled_news_symbols
                    ON crawled_news(symbols);
            """)

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_batch(self, items: List[CrawledNewsItem]) -> int:
        """
        批量保存新闻（自动去重）

        Returns:
            实际新增条数
        """
        if not items:
            return 0

        inserted = 0
        with self._write_lock:
            with self._get_conn() as conn:
                for item in items:
                    try:
                        row = item.to_db_dict()
                        conn.execute("""
                            INSERT OR IGNORE INTO crawled_news
                            (id, source, source_url, author, title, content,
                             publish_time, crawl_time, symbols, markets, tags,
                             summary, sentiment_score, sentiment_label,
                             importance, language, is_processed, dedupe_key)
                            VALUES
                            (:id, :source, :source_url, :author, :title, :content,
                             :publish_time, :crawl_time, :symbols, :markets, :tags,
                             :summary, :sentiment_score, :sentiment_label,
                             :importance, :language, :is_processed, :dedupe_key)
                        """, row)
                        if conn.total_changes:
                            inserted += 1
                    except sqlite3.IntegrityError:
                        # 重复条目，跳过
                        pass
                    except Exception as e:
                        logger.warning(f"[NewsRepo] 保存失败: {e}, title={item.title[:30]}")

        logger.info(f"[NewsRepo] 批量保存: 新增 {inserted}/{len(items)} 条")
        return inserted

    def get_unprocessed(self, limit: int = 50) -> List[CrawledNewsItem]:
        """获取未经 LLM 处理的新闻"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM crawled_news
                WHERE is_processed = 0
                ORDER BY crawl_time DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

        return [self._row_to_item(r) for r in rows]

    def mark_processed(self, news_id: str, summary: Optional[str],
                       sentiment_score: Optional[float],
                       sentiment_label: Optional[str],
                       importance: Optional[str]):
        """标记为已处理并更新 LLM 结果"""
        with self._write_lock:
            with self._get_conn() as conn:
                conn.execute("""
                    UPDATE crawled_news
                    SET is_processed = 1,
                        summary = ?,
                        sentiment_score = ?,
                        sentiment_label = ?,
                        importance = ?
                    WHERE id = ?
                """, (summary, sentiment_score, sentiment_label, importance, news_id))

    def query_news(
        self,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CrawledNewsItem]:
        """查询新闻"""
        conditions = []
        params = []

        if symbol:
            conditions.append("symbols LIKE ?")
            params.append(f'%"{symbol}"%')
        if source:
            conditions.append("source = ?")
            params.append(source)
        if start_time:
            conditions.append("publish_time >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("publish_time <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_conn() as conn:
            cursor = conn.execute(f"""
                SELECT * FROM crawled_news
                WHERE {where_clause}
                ORDER BY publish_time DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            rows = cursor.fetchall()

        return [self._row_to_item(r) for r in rows]

    def count_news(self, hours: int = 24) -> dict:
        """统计最近 N 小时采集数据"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT source, COUNT(*) as cnt
                FROM crawled_news
                WHERE crawl_time >= datetime('now', ? || ' hours')
                GROUP BY source
            """, (f"-{hours}",))
            rows = cursor.fetchall()

        return {row["source"]: row["cnt"] for row in rows}

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> CrawledNewsItem:
        """DB Row → CrawledNewsItem"""
        return CrawledNewsItem(
            id=row["id"],
            source=row["source"],
            source_url=row["source_url"],
            author=row["author"],
            title=row["title"],
            content=row["content"],
            publish_time=(
                datetime.fromisoformat(row["publish_time"])
                if row["publish_time"] else None
            ),
            crawl_time=datetime.fromisoformat(row["crawl_time"]),
            symbols=json.loads(row["symbols"] or "[]"),
            markets=json.loads(row["markets"] or "[]"),
            tags=json.loads(row["tags"] or "[]"),
            summary=row["summary"],
            sentiment_score=row["sentiment_score"],
            sentiment_label=(
                NewsSentimentLabel(row["sentiment_label"])
                if row["sentiment_label"] else None
            ),
            importance=(
                NewsImportance(row["importance"])
                if row["importance"] else None
            ),
            language=row["language"],
            is_processed=bool(row["is_processed"]),
        )
