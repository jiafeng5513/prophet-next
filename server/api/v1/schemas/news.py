# -*- coding: utf-8 -*-
"""
===================================
新闻流相关模型
===================================

职责：
1. 定义新闻列表和详情模型
2. 定义新闻刷新请求/响应模型
3. 定义新闻时间线聚合模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class NewsListItem(BaseModel):
    """新闻列表条目"""

    id: int = Field(..., description="新闻 ID")
    title: str = Field(..., description="新闻标题")
    snippet: str = Field("", description="新闻摘要")
    url: str = Field("", description="新闻链接")
    source: str = Field("", description="新闻来源")
    published_date: Optional[str] = Field(None, description="发布时间")
    code: str = Field("", description="股票代码")
    name: str = Field("", description="股票名称")
    dimension: str = Field("", description="新闻维度")


class NewsListResponse(BaseModel):
    """新闻列表分页响应"""

    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    items: List[NewsListItem] = Field(default_factory=list, description="新闻列表")


class NewsDetailResponse(NewsListItem):
    """新闻详情响应"""

    fetched_at: Optional[str] = Field(None, description="入库时间")
    query: str = Field("", description="搜索关键词")
    provider: str = Field("", description="搜索引擎")


class NewsRefreshRequest(BaseModel):
    """主动刷新新闻请求"""

    codes: List[str] = Field(default_factory=list, description="股票代码列表")
    keywords: List[str] = Field(default_factory=list, description="搜索关键词列表")
    max_results: int = Field(default=10, ge=1, le=50, description="每项最大结果数")


class NewsRefreshResponse(BaseModel):
    """主动刷新新闻响应"""

    fetched: int = Field(..., description="获取的新闻条数")
    new_count: int = Field(..., description="新增的新闻条数")
    message: str = Field(..., description="提示信息")


class NewsTimelineItem(BaseModel):
    """时间线中的新闻条目（精简）"""

    id: int = Field(..., description="新闻 ID")
    title: str = Field(..., description="新闻标题")
    source: str = Field("", description="新闻来源")
    published_date: Optional[str] = Field(None, description="发布时间")
    code: str = Field("", description="股票代码")
    name: str = Field("", description="股票名称")


class NewsTimelineGroup(BaseModel):
    """按日期分组的新闻"""

    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    items: List[NewsTimelineItem] = Field(default_factory=list, description="该日新闻列表")


class NewsTimelineResponse(BaseModel):
    """新闻时间线响应"""

    groups: List[NewsTimelineGroup] = Field(default_factory=list, description="按日期分组的新闻")
