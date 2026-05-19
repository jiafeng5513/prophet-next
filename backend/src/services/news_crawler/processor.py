# -*- coding: utf-8 -*-
"""
===================================
新闻 LLM 处理器
===================================

职责：
1. 对未处理新闻进行摘要提取
2. 情感分析（-1.0 ~ 1.0）
3. 重要性分级
4. 批量处理以控制 API 成本
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional

from src.enums import NewsImportance, NewsSentimentLabel
from src.services.news_crawler.models import CrawledNewsItem
from src.services.news_crawler.repository import NewsRepository

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一个金融新闻分析助手。对于给定的新闻，请返回 JSON 格式分析结果：
{
  "summary": "一句话摘要（不超过50字）",
  "sentiment_score": 0.0,  // -1.0(极度利空) ~ 1.0(极度利好)，对市场的影响
  "importance": "high/medium/low"  // 对投资者的重要程度
}

判断标准：
- high: 重大政策、央行决议、公司重大公告（并购/退市/财报超预期）
- medium: 行业动态、机构观点、中等影响的政策
- low: 一般消息、个人观点、市场噪音

只返回 JSON，不要其他文字。"""


class NewsProcessor:
    """新闻 LLM 处理器"""

    def __init__(self, batch_size: int = 10):
        self._batch_size = batch_size
        self._repo = NewsRepository()
        self._adapter = None  # lazy init

    def _get_adapter(self):
        """懒加载 LLM 适配器"""
        if self._adapter is None:
            from src.agent.llm_adapter import LLMToolAdapter
            from src.config import get_config
            config = get_config()
            self._adapter = LLMToolAdapter(config)
        return self._adapter

    async def process_pending(self, limit: int = 50) -> int:
        """
        处理待分析新闻

        Returns:
            成功处理条数
        """
        items = self._repo.get_unprocessed(limit=limit)
        if not items:
            return 0

        processed = 0

        # 分批处理
        for i in range(0, len(items), self._batch_size):
            batch = items[i:i + self._batch_size]
            results = await self._process_batch(batch)
            processed += results

        logger.info(f"[NewsProcessor] 处理完成: {processed}/{len(items)}")
        return processed

    async def _process_batch(self, items: List[CrawledNewsItem]) -> int:
        """处理一批新闻"""
        success = 0
        for item in items:
            try:
                result = await self._analyze_single(item)
                if result:
                    self._repo.mark_processed(
                        news_id=item.id,
                        summary=result.get("summary"),
                        sentiment_score=result.get("sentiment_score"),
                        sentiment_label=NewsSentimentLabel.from_score(
                            result.get("sentiment_score", 0)
                        ).value,
                        importance=result.get("importance", "low"),
                    )
                    success += 1
            except Exception as e:
                logger.warning(
                    f"[NewsProcessor] 分析失败: {e}, title={item.title[:30]}"
                )
            # 控制速率
            await asyncio.sleep(0.5)

        return success

    async def _analyze_single(self, item: CrawledNewsItem) -> Optional[dict]:
        """分析单条新闻"""
        adapter = self._get_adapter()

        content = item.title
        if item.content and item.content != item.title:
            content += f"\n{item.content[:500]}"

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        try:
            response = adapter.call_text(
                messages=messages,
                temperature=0.3,
                max_tokens=256,
            )

            # 解析 JSON 结果
            text = response.content.strip()
            # 移除可能的 markdown 代码块包裹
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

            result = json.loads(text)

            # 验证字段
            score = float(result.get("sentiment_score", 0))
            score = max(-1.0, min(1.0, score))  # clamp
            result["sentiment_score"] = score

            importance = result.get("importance", "low")
            if importance not in ("high", "medium", "low"):
                importance = "low"
            result["importance"] = importance

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"[NewsProcessor] JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"[NewsProcessor] LLM 调用失败: {e}")
            return None

    async def process_items_directly(self, items: List[CrawledNewsItem]) -> int:
        """
        直接处理传入的新闻列表（由 scheduler 回调触发）

        Returns:
            成功处理条数
        """
        if not items:
            return 0
        return await self._process_batch(items)
