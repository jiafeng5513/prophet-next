# -*- coding: utf-8 -*-
"""
===================================
新闻流 Service 层
===================================

职责：
1. 封装新闻查询逻辑（分页、筛选、搜索）
2. 封装新闻主动刷新逻辑
3. 提供时间线聚合查询
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, and_, desc, func, or_

from src.storage import DatabaseManager, NewsIntel

logger = logging.getLogger(__name__)


class NewsService:
    """新闻流服务"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_news_list(
        self,
        page: int = 1,
        page_size: int = 30,
        code: Optional[str] = None,
        keyword: Optional[str] = None,
        dimension: Optional[str] = None,
        days: int = 7,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        分页查询新闻列表

        Returns:
            (total, items) 元组
        """
        cutoff = datetime.now() - timedelta(days=days)
        offset = (page - 1) * page_size

        with self.db.get_session() as session:
            # 构建基础过滤条件
            conditions = [NewsIntel.fetched_at >= cutoff]
            if code:
                conditions.append(NewsIntel.code == code)
            if dimension:
                conditions.append(NewsIntel.dimension == dimension)
            if keyword:
                like_pattern = f"%{keyword}%"
                conditions.append(
                    or_(
                        NewsIntel.title.ilike(like_pattern),
                        NewsIntel.snippet.ilike(like_pattern),
                    )
                )

            where_clause = and_(*conditions)

            # 查询总数
            total = session.execute(
                select(func.count(NewsIntel.id)).where(where_clause)
            ).scalar() or 0

            # 查询数据
            rows = session.execute(
                select(NewsIntel)
                .where(where_clause)
                .order_by(
                    desc(func.coalesce(NewsIntel.published_date, NewsIntel.fetched_at))
                )
                .offset(offset)
                .limit(page_size)
            ).scalars().all()

            items = [self._row_to_dict(r) for r in rows]

        return total, items

    def get_news_detail(self, news_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取新闻详情"""
        with self.db.get_session() as session:
            row = session.execute(
                select(NewsIntel).where(NewsIntel.id == news_id)
            ).scalar_one_or_none()
            if not row:
                return None
            return self._row_to_detail_dict(row)

    def get_news_timeline(
        self,
        code: Optional[str] = None,
        keyword: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        按日期分组返回新闻（时间线格式）

        Returns:
            [{ date: "2026-04-25", items: [...] }, ...]
        """
        cutoff = datetime.now() - timedelta(days=days)

        with self.db.get_session() as session:
            conditions = [NewsIntel.fetched_at >= cutoff]
            if code:
                conditions.append(NewsIntel.code == code)
            if keyword:
                like_pattern = f"%{keyword}%"
                conditions.append(
                    or_(
                        NewsIntel.title.ilike(like_pattern),
                        NewsIntel.snippet.ilike(like_pattern),
                    )
                )

            rows = session.execute(
                select(NewsIntel)
                .where(and_(*conditions))
                .order_by(
                    desc(func.coalesce(NewsIntel.published_date, NewsIntel.fetched_at))
                )
                .limit(limit)
            ).scalars().all()

        # 按日期分组
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            dt = r.published_date or r.fetched_at or datetime.now()
            date_key = dt.strftime("%Y-%m-%d") if isinstance(dt, datetime) else str(dt)[:10]
            grouped[date_key].append({
                "id": r.id,
                "title": r.title or "",
                "source": r.source or "",
                "published_date": self._fmt_datetime(r.published_date),
                "code": r.code or "",
                "name": r.name or "",
            })

        # 按日期倒序排列
        groups = [
            {"date": date_key, "items": items}
            for date_key, items in sorted(grouped.items(), reverse=True)
        ]
        return groups

    def refresh_news(
        self,
        codes: List[str],
        keywords: List[str],
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        主动刷新新闻：调用 SearchService 搜索并入库

        Returns:
            { fetched, new_count, message }
        """
        from src.search_service import get_search_service

        search_service = get_search_service()
        total_fetched = 0
        total_new = 0

        # 按股票代码搜索
        for code in codes:
            stock_name = self._resolve_stock_name(code)
            try:
                response = search_service.search_stock_news(
                    stock_code=code,
                    stock_name=stock_name,
                    max_results=max_results,
                )
                if response and response.results:
                    total_fetched += len(response.results)
                    new_count = self.db.save_news_intel(
                        code=code,
                        name=stock_name,
                        dimension="latest_news",
                        query=response.query,
                        response=response,
                        query_context={"query_source": "web"},
                    )
                    total_new += new_count
            except Exception as e:
                logger.error(f"刷新股票 {code} 新闻失败: {e}", exc_info=True)

        # 按关键词搜索（借用 search_stock_news 的 focus_keywords 参数）
        for kw in keywords:
            try:
                response = search_service.search_stock_news(
                    stock_code="",
                    stock_name="",
                    max_results=max_results,
                    focus_keywords=[kw],
                )
                if response and response.results:
                    total_fetched += len(response.results)
                    new_count = self.db.save_news_intel(
                        code="",
                        name="",
                        dimension="latest_news",
                        query=kw,
                        response=response,
                        query_context={"query_source": "web"},
                    )
                    total_new += new_count
            except Exception as e:
                logger.error(f"刷新关键词 '{kw}' 新闻失败: {e}", exc_info=True)

        return {
            "fetched": total_fetched,
            "new_count": total_new,
            "message": f"成功获取 {total_fetched} 条新闻，其中 {total_new} 条为新增",
        }

    def _resolve_stock_name(self, code: str) -> str:
        """尝试从数据库最近新闻中获取股票名称"""
        try:
            recent = self.db.get_recent_news(code=code, days=30, limit=1)
            if recent and recent[0].name:
                return recent[0].name
        except Exception:
            pass
        return code

    @staticmethod
    def _fmt_datetime(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return str(dt)

    @staticmethod
    def _row_to_dict(r: NewsIntel) -> Dict[str, Any]:
        snippet = (r.snippet or "").strip()
        if len(snippet) > 200:
            snippet = f"{snippet[:197]}..."
        return {
            "id": r.id,
            "title": r.title or "",
            "snippet": snippet,
            "url": r.url or "",
            "source": r.source or "",
            "published_date": NewsService._fmt_datetime(r.published_date),
            "code": r.code or "",
            "name": r.name or "",
            "dimension": r.dimension or "",
        }

    @staticmethod
    def _row_to_detail_dict(r: NewsIntel) -> Dict[str, Any]:
        return {
            "id": r.id,
            "title": r.title or "",
            "snippet": (r.snippet or "").strip(),
            "url": r.url or "",
            "source": r.source or "",
            "published_date": NewsService._fmt_datetime(r.published_date),
            "fetched_at": NewsService._fmt_datetime(r.fetched_at),
            "code": r.code or "",
            "name": r.name or "",
            "dimension": r.dimension or "",
            "query": r.query or "",
            "provider": r.provider or "",
        }
