# -*- coding: utf-8 -*-
"""
===================================
新闻采集数据模型
===================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.enums import MarketType, NewsImportance, NewsSentimentLabel


@dataclass
class CrawledNewsItem:
    """
    采集到的新闻条目（统一格式）

    每个爬虫产出此对象，交由 scheduler 持久化。
    """

    # 唯一标识
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    # 来源信息
    source: str = ""                  # "eastmoney" / "xueqiu" / "sina" / "cls"
    source_url: str = ""              # 原始 URL（去重键）
    author: Optional[str] = None

    # 核心内容
    title: str = ""
    content: str = ""                 # 全文或摘要
    publish_time: Optional[datetime] = None
    crawl_time: datetime = field(default_factory=datetime.utcnow)

    # 关联信息
    symbols: List[str] = field(default_factory=list)    # 关联标的 ["600519", "AAPL"]
    markets: List[str] = field(default_factory=list)    # ["A_SHARE", "US"]
    tags: List[str] = field(default_factory=list)       # ["earnings", "macro"]

    # LLM 处理结果（采集时为空，由 processor 填充）
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None             # -1.0 ~ 1.0
    sentiment_label: Optional[NewsSentimentLabel] = None
    importance: Optional[NewsImportance] = None

    # 元数据
    language: str = "zh"              # "zh" / "en"
    view_count: Optional[int] = None
    comment_count: Optional[int] = None
    is_processed: bool = False        # 是否已 LLM 处理

    @property
    def dedupe_key(self) -> str:
        """去重键：(source, source_url)"""
        return f"{self.source}#{self.source_url}"

    def to_db_dict(self) -> dict:
        """转为数据库插入用的字典"""
        import json
        return {
            "id": self.id,
            "source": self.source,
            "source_url": self.source_url,
            "author": self.author,
            "title": self.title,
            "content": self.content,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "crawl_time": self.crawl_time.isoformat(),
            "symbols": json.dumps(self.symbols, ensure_ascii=False),
            "markets": json.dumps(self.markets, ensure_ascii=False),
            "tags": json.dumps(self.tags, ensure_ascii=False),
            "summary": self.summary,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label.value if self.sentiment_label else None,
            "importance": self.importance.value if self.importance else None,
            "language": self.language,
            "is_processed": 1 if self.is_processed else 0,
            "dedupe_key": self.dedupe_key,
        }
