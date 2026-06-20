# -*- coding: utf-8 -*-
"""
===================================
东方财富新闻爬虫
===================================

采集来源：
1. 东方财富全球财经快讯 (kuaixun API)
2. 东方财富股吧热帖 (可选)

频率：每 5 分钟拉取一次快讯列表
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

import aiohttp

from src.services.news_crawler.base_crawler import BaseCrawler
from src.services.news_crawler.models import CrawledNewsItem

logger = logging.getLogger(__name__)

# 东方财富全球快讯 API
_KUAIXUN_API = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"

# 财联社快讯 API（备用）
_CLS_API = "https://www.cls.cn/nodeapi/updateTelegraph"

# 请求头
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://kuaixun.eastmoney.com/",
    "Accept": "application/json",
}


class EastMoneyCrawler(BaseCrawler):
    """
    东方财富全球快讯爬虫

    API 返回格式（简化）：
    {
        "data": {
            "list": [
                {
                    "art_uniqueUrl": "...",
                    "title": "...",
                    "content": "...",
                    "showTime": "2024-01-01 10:30:00",
                    "mediaName": "...",
                    "Art_Url": "...",
                }
            ]
        }
    }
    """

    def __init__(self, enabled: bool = True):
        super().__init__(source_name="eastmoney", enabled=enabled)
        # 默认采集的栏目 columns
        # 350 = A股快讯, 353 = 全球快讯, 356 = 港股快讯, 359 = 美股快讯
        self._columns: List[str] = ["350", "353"]

    async def fetch_news(
        self,
        limit: int = 50,
        keywords: Optional[List[str]] = None,
    ) -> List[CrawledNewsItem]:
        """采集东方财富快讯"""
        if not self.enabled:
            return []

        items: List[CrawledNewsItem] = []

        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                for column in self._columns:
                    fetched = await self._fetch_column(session, column, limit)
                    items.extend(fetched)
        except Exception as e:
            logger.error(f"[EastMoneyCrawler] 采集异常: {e}")

        # 关键词过滤
        if keywords:
            lower_kws = [kw.lower() for kw in keywords]
            items = [
                item for item in items
                if any(kw in item.title.lower() or kw in item.content.lower()
                       for kw in lower_kws)
            ]

        logger.info(f"[EastMoneyCrawler] 本轮采集 {len(items)} 条新闻")
        return items

    async def _fetch_column(
        self,
        session: aiohttp.ClientSession,
        column: str,
        limit: int,
    ) -> List[CrawledNewsItem]:
        """采集单个栏目"""
        params = {
            "column": column,
            "boardCode": "",
            "pageSize": str(min(limit, 100)),
            "lastTime": "",
            "type": "0",
        }

        try:
            async with session.get(
                _KUAIXUN_API, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"[EastMoneyCrawler] 栏目 {column} HTTP {resp.status}"
                    )
                    return []

                data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"[EastMoneyCrawler] 栏目 {column} 请求失败: {e}")
            return []

        # 解析
        news_list = (data or {}).get("data", {}).get("list", [])
        items: List[CrawledNewsItem] = []

        for raw in news_list:
            item = self._parse_item(raw, column)
            if item:
                items.append(item)

        return items

    def _parse_item(self, raw: dict, column: str) -> Optional[CrawledNewsItem]:
        """解析单条新闻"""
        title = (raw.get("title") or "").strip()
        content = (raw.get("content") or "").strip()
        url = (raw.get("Art_Url") or raw.get("art_uniqueUrl") or "").strip()

        if not title and not content:
            return None

        # 解析时间
        show_time_str = raw.get("showTime", "")
        publish_time = None
        if show_time_str:
            try:
                publish_time = datetime.strptime(show_time_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

        # 提取关联股票代码
        text_for_extract = f"{title} {content}"
        symbols = self.extract_symbols(text_for_extract)

        # 根据栏目推断市场
        markets = self._column_to_markets(column)

        return CrawledNewsItem(
            source=self.source_name,
            source_url=url,
            author=raw.get("mediaName"),
            title=title,
            content=content,
            publish_time=publish_time,
            symbols=symbols,
            markets=markets,
            tags=self._extract_tags(raw),
            language="zh",
        )

    @staticmethod
    def _column_to_markets(column: str) -> List[str]:
        """栏目号 → 市场类型"""
        mapping = {
            "350": ["A_SHARE"],
            "353": ["A_SHARE", "US", "HK"],   # 全球
            "356": ["HK"],
            "359": ["US"],
        }
        return mapping.get(column, [])

    @staticmethod
    def _extract_tags(raw: dict) -> List[str]:
        """从原始数据中提取标签"""
        tags = []
        if raw.get("digest_type"):
            tags.append(f"digest_{raw['digest_type']}")
        if raw.get("importance"):
            tags.append("important")
        return tags
