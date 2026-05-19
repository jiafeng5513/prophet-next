# -*- coding: utf-8 -*-
"""
===================================
新闻采集子系统
===================================

持续采集财经新闻/社交媒体信息，清洗后持久化为可回测的结构化数据集。

模块结构：
- models.py      — 新闻数据模型
- base_crawler.py — 爬虫基类
- eastmoney_crawler.py — 东方财富爬虫
- scheduler.py   — 采集调度器
- processor.py   — LLM 增强处理器
- repository.py  — 数据访问层
"""

from src.services.news_crawler.models import CrawledNewsItem
from src.services.news_crawler.base_crawler import BaseCrawler
from src.services.news_crawler.scheduler import NewsCrawlScheduler
from src.services.news_crawler.processor import NewsProcessor
from src.services.news_crawler.repository import NewsRepository

__all__ = [
    "CrawledNewsItem",
    "BaseCrawler",
    "NewsCrawlScheduler",
    "NewsProcessor",
    "NewsRepository",
]
