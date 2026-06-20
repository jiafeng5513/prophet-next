# -*- coding: utf-8 -*-
"""
===================================
新闻采集系统接口
===================================

职责：
1. GET  /api/v1/news-crawler/status  — 采集器状态
2. POST /api/v1/news-crawler/start   — 启动采集
3. POST /api/v1/news-crawler/stop    — 停止采集
4. POST /api/v1/news-crawler/run-once — 手动触发一轮
5. GET  /api/v1/news-crawler/feed    — 查询采集到的新闻流
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.news_crawler.scheduler import NewsCrawlScheduler
from src.services.news_crawler.eastmoney_crawler import EastMoneyCrawler
from src.services.news_crawler.processor import NewsProcessor
from src.services.news_crawler.repository import NewsRepository

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 processor 实例
_processor = NewsProcessor(batch_size=5)


def _get_scheduler() -> NewsCrawlScheduler:
    """获取 scheduler 单例并确保爬虫已注册"""
    scheduler = NewsCrawlScheduler.get_instance()
    # 自动注册默认爬虫（幂等）
    if "eastmoney" not in scheduler._crawlers:
        scheduler.register_crawler(EastMoneyCrawler())
        # 设置新条目回调 → LLM 处理
        scheduler.set_on_new_items(_processor.process_items_directly)
    return scheduler


# ──── Schemas ────

class CrawlerStatusResponse(BaseModel):
    running: bool
    interval_seconds: int
    crawlers: dict
    last_24h_stats: dict


class RunOnceResponse(BaseModel):
    new_items: int


class StartRequest(BaseModel):
    interval_seconds: int = Field(default=300, ge=60, le=3600)


class FeedItem(BaseModel):
    id: str
    source: str
    title: str
    content: str = ""
    publish_time: Optional[str] = None
    symbols: list = []
    markets: list = []
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    importance: Optional[str] = None
    is_processed: bool = False


class FeedResponse(BaseModel):
    total: int
    items: list


# ──── Endpoints ────

@router.get(
    "/status",
    response_model=CrawlerStatusResponse,
    summary="获取采集器状态",
)
def get_crawler_status() -> CrawlerStatusResponse:
    """获取新闻采集调度器状态"""
    scheduler = _get_scheduler()
    status = scheduler.get_status()
    return CrawlerStatusResponse(**status)


@router.post(
    "/start",
    response_model=CrawlerStatusResponse,
    summary="启动新闻采集",
)
async def start_crawler(request: StartRequest = StartRequest()) -> CrawlerStatusResponse:
    """启动定时新闻采集"""
    scheduler = _get_scheduler()

    if scheduler.is_running:
        raise HTTPException(status_code=409, detail="采集器已在运行中")

    scheduler.interval_seconds = request.interval_seconds
    await scheduler.start()

    status = scheduler.get_status()
    return CrawlerStatusResponse(**status)


@router.post(
    "/stop",
    response_model=CrawlerStatusResponse,
    summary="停止新闻采集",
)
async def stop_crawler() -> CrawlerStatusResponse:
    """停止定时新闻采集"""
    scheduler = _get_scheduler()
    await scheduler.stop()

    status = scheduler.get_status()
    return CrawlerStatusResponse(**status)


@router.post(
    "/run-once",
    response_model=RunOnceResponse,
    summary="手动触发一轮采集",
)
async def run_once() -> RunOnceResponse:
    """手动触发一次采集（不影响定时任务）"""
    scheduler = _get_scheduler()
    count = await scheduler.run_once()
    return RunOnceResponse(new_items=count)


@router.get(
    "/feed",
    response_model=FeedResponse,
    summary="查询采集的新闻流",
)
def get_news_feed(
    symbol: Optional[str] = Query(None, description="按标的筛选"),
    source: Optional[str] = Query(None, description="按来源筛选"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FeedResponse:
    """查询采集到的新闻流"""
    repo = NewsRepository()
    items = repo.query_news(
        symbol=symbol,
        source=source,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    feed_items = [
        FeedItem(
            id=item.id,
            source=item.source,
            title=item.title,
            content=item.content[:200] if item.content else "",
            publish_time=item.publish_time.isoformat() if item.publish_time else None,
            symbols=item.symbols,
            markets=item.markets,
            summary=item.summary,
            sentiment_score=item.sentiment_score,
            sentiment_label=item.sentiment_label.value if item.sentiment_label else None,
            importance=item.importance.value if item.importance else None,
            is_processed=item.is_processed,
        )
        for item in items
    ]

    return FeedResponse(total=len(feed_items), items=feed_items)


@router.post(
    "/process",
    summary="手动触发 LLM 处理未分析新闻",
)
async def process_pending(
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """手动触发 LLM 处理等待中的新闻"""
    count = await _processor.process_pending(limit=limit)
    return {"processed": count}
