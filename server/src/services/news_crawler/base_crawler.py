# -*- coding: utf-8 -*-
"""
===================================
新闻爬虫基类
===================================

所有新闻源爬虫的抽象基类。
子类实现 fetch_news() 和 extract_symbols() 方法。
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from src.services.news_crawler.models import CrawledNewsItem

logger = logging.getLogger(__name__)

# A股代码正则：6位数字
_ASHARE_PATTERN = re.compile(r'(?<!\d)([036]\d{5})(?!\d)')
# 港股代码正则：HK + 5位数字 或纯5位数字前缀为0
_HK_PATTERN = re.compile(r'(?:HK)?(\d{5})\.HK\b', re.IGNORECASE)
# 美股代码正则：1-5位大写字母（排除常见英文词汇）
_US_PATTERN = re.compile(r'\b([A-Z]{1,5})\b')
_US_NOISE_WORDS = frozenset([
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
    "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET",
    "HAS", "HIM", "HIS", "HOW", "MAN", "NEW", "NOW", "OLD",
    "SEE", "WAY", "WHO", "DID", "ITS", "LET", "SAY", "SHE",
    "TOO", "USE", "CEO", "CFO", "IPO", "GDP", "CPI", "PPI",
    "ETF", "API", "USD", "CNY", "HKD", "EUR", "GBP",
])


class BaseCrawler(ABC):
    """新闻爬虫基类"""

    def __init__(self, source_name: str, enabled: bool = True):
        self.source_name = source_name
        self.enabled = enabled
        self._last_crawl_cursor: Optional[str] = None

    @property
    def last_crawl_cursor(self) -> Optional[str]:
        return self._last_crawl_cursor

    @last_crawl_cursor.setter
    def last_crawl_cursor(self, value: Optional[str]):
        self._last_crawl_cursor = value

    @abstractmethod
    async def fetch_news(
        self,
        limit: int = 50,
        keywords: Optional[List[str]] = None,
    ) -> List[CrawledNewsItem]:
        """
        抓取新闻列表

        Args:
            limit: 最大返回条数
            keywords: 关键词过滤（可选）

        Returns:
            新闻列表（未去重，由 scheduler 去重）
        """
        ...

    def extract_symbols(self, text: str) -> List[str]:
        """
        从文本中提取股票代码

        默认实现：正则匹配 A股6位数字代码。
        子类可覆盖以支持特定源的格式。
        """
        if not text:
            return []

        symbols = set()

        # A股
        for match in _ASHARE_PATTERN.finditer(text):
            code = match.group(1)
            # 排除明显非股票的数字（如年份 2024xx）
            if not code.startswith("20") and not code.startswith("19"):
                symbols.add(code)

        # 美股（从英文内容中提取）
        for match in _US_PATTERN.finditer(text):
            word = match.group(1)
            if len(word) >= 2 and word not in _US_NOISE_WORDS:
                # 简单启发式：只保留常见美股代码长度
                if 2 <= len(word) <= 4:
                    symbols.add(word)

        return list(symbols)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source={self.source_name}, enabled={self.enabled})>"
