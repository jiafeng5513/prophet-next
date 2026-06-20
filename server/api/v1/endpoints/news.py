# -*- coding: utf-8 -*-
"""
===================================
新闻流接口
===================================

职责：
1. 提供 GET /api/v1/news/timeline 新闻时间线接口
2. 提供 GET /api/v1/news 新闻列表分页接口
3. 提供 GET /api/v1/news/{news_id} 新闻详情接口
4. 提供 POST /api/v1/news/refresh 主动刷新新闻接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from api.deps import get_database_manager
from api.v1.schemas.news import (
    NewsListItem,
    NewsListResponse,
    NewsDetailResponse,
    NewsRefreshRequest,
    NewsRefreshResponse,
    NewsTimelineItem,
    NewsTimelineGroup,
    NewsTimelineResponse,
)
from api.v1.schemas.common import ErrorResponse
from src.storage import DatabaseManager
from src.services.news_service import NewsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/timeline",
    response_model=NewsTimelineResponse,
    responses={
        200: {"description": "按日期分组的新闻时间线"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取新闻时间线",
    description="按日期分组返回新闻，支持按股票代码和关键词筛选",
)
def get_news_timeline(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    days: int = Query(7, ge=1, le=90, description="时间范围（天）"),
    limit: int = Query(100, ge=1, le=500, description="总条数上限"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> NewsTimelineResponse:
    """获取新闻时间线（按日期分组）"""
    try:
        service = NewsService(db_manager)
        groups = service.get_news_timeline(
            code=code, keyword=keyword, days=days, limit=limit
        )

        response_groups = [
            NewsTimelineGroup(
                date=g["date"],
                items=[
                    NewsTimelineItem(**item)
                    for item in g["items"]
                ],
            )
            for g in groups
        ]

        return NewsTimelineResponse(groups=response_groups)

    except Exception as e:
        logger.error(f"查询新闻时间线失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询新闻时间线失败: {str(e)}"},
        )


@router.get(
    "",
    response_model=NewsListResponse,
    responses={
        200: {"description": "新闻列表"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取新闻列表",
    description="分页获取新闻列表，支持按股票代码、关键词、维度筛选",
)
def get_news_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页条数"),
    code: Optional[str] = Query(None, description="股票代码筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索（匹配标题/摘要）"),
    dimension: Optional[str] = Query(None, description="维度筛选"),
    days: int = Query(7, ge=1, le=90, description="时间范围（天）"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> NewsListResponse:
    """分页获取新闻列表"""
    try:
        service = NewsService(db_manager)
        total, items = service.get_news_list(
            page=page,
            page_size=page_size,
            code=code,
            keyword=keyword,
            dimension=dimension,
            days=days,
        )

        response_items = [NewsListItem(**item) for item in items]

        return NewsListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=response_items,
        )

    except Exception as e:
        logger.error(f"查询新闻列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询新闻列表失败: {str(e)}"},
        )


@router.get(
    "/{news_id}",
    response_model=NewsDetailResponse,
    responses={
        200: {"description": "新闻详情"},
        404: {"description": "新闻不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取新闻详情",
    description="根据新闻 ID 获取完整新闻详情",
)
def get_news_detail(
    news_id: int,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> NewsDetailResponse:
    """获取新闻详情"""
    try:
        service = NewsService(db_manager)
        detail = service.get_news_detail(news_id)
        if not detail:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"新闻 {news_id} 不存在"},
            )
        return NewsDetailResponse(**detail)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询新闻详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"查询新闻详情失败: {str(e)}"},
        )


@router.post(
    "/refresh",
    response_model=NewsRefreshResponse,
    responses={
        200: {"description": "刷新结果"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="主动刷新新闻",
    description="手动触发为指定股票或关键词搜索最新新闻并入库",
)
def refresh_news(
    request: NewsRefreshRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> NewsRefreshResponse:
    """主动刷新新闻"""
    if not request.codes and not request.keywords:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "codes 和 keywords 不能同时为空"},
        )

    try:
        service = NewsService(db_manager)
        result = service.refresh_news(
            codes=request.codes,
            keywords=request.keywords,
            max_results=request.max_results,
        )
        return NewsRefreshResponse(**result)

    except Exception as e:
        logger.error(f"刷新新闻失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"刷新新闻失败: {str(e)}"},
        )
