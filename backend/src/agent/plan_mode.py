# -*- coding: utf-8 -*-
"""
Plan Mode Handler — 先生成分析计划，等用户确认后再执行。

流程:
1. 用户发送分析请求 (mode=plan)
2. LLM 快速生成分析计划 (步骤列表 + 预估耗时)
3. 通过 SSE 事件 plan_ready 返回前端
4. 前端展示计划 → 用户点击执行
5. 前端发送 confirm → 后端执行完整管线 (full/specialist)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.agent.llm_adapter import LLMToolAdapter
from src.agent.protocols import AgentContext

logger = logging.getLogger(__name__)

# 默认分析计划步骤模板（当 LLM 生成失败时回退）
_DEFAULT_PLAN_STEPS = [
    {"description": "获取近30日K线 + 技术指标分析", "type": "technical"},
    {"description": "搜索近期新闻 + 公告情报", "type": "intel"},
    {"description": "Bull/Bear 多空辩论 (2轮)", "type": "debate"},
    {"description": "风险三方讨论 (激进/保守/中立)", "type": "risk"},
    {"description": "综合决策 + 生成报告", "type": "decision"},
]

PLAN_GENERATION_PROMPT = """\
你是一个股票分析计划生成器。根据用户的分析请求，生成一份结构化的分析计划。

用户请求: {query}
标的代码: {stock_code}

请输出 JSON 格式的分析计划:
{{
  "steps": [
    {{"description": "步骤描述", "type": "technical|intel|debate|risk|decision"}}
  ],
  "estimated_time": "预估耗时 (如 '30-45秒')",
  "estimated_tokens": 预估 token 数 (整数),
  "mode_recommendation": "full 或 specialist"
}}

注意:
- 根据标的类型(A股/美股/加密)调整步骤
- 如果请求较简单,可省略辩论/风险步骤
- estimated_tokens 预估总消耗 (含数据获取 + LLM 调用)
"""


@dataclass
class AnalysisPlan:
    """分析计划数据结构"""

    steps: List[Dict[str, str]] = field(default_factory=list)
    estimated_time: str = ""
    estimated_tokens: int = 0
    mode_recommendation: str = "full"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "estimated_time": self.estimated_time,
            "estimated_tokens": self.estimated_tokens,
            "mode_recommendation": self.mode_recommendation,
        }


class PlanModeHandler:
    """Plan 模式处理器: 生成计划 → 等待确认 → 执行管线"""

    def __init__(self, llm_adapter: LLMToolAdapter):
        self.llm_adapter = llm_adapter

    def generate_plan(
        self,
        ctx: AgentContext,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> AnalysisPlan:
        """用快速模型生成分析计划。

        Args:
            ctx: Agent 上下文 (含 query, stock_code)
            progress_callback: SSE 事件回调

        Returns:
            AnalysisPlan 实例
        """
        if progress_callback:
            progress_callback({"type": "thinking", "content": "正在生成分析计划..."})

        prompt = PLAN_GENERATION_PROMPT.format(
            query=ctx.query,
            stock_code=ctx.stock_code or "未指定",
        )

        try:
            response = self.llm_adapter.call(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
                response_format={"type": "json_object"},
            )

            if response.content:
                plan_data = json.loads(response.content)
                plan = AnalysisPlan(
                    steps=plan_data.get("steps", _DEFAULT_PLAN_STEPS),
                    estimated_time=plan_data.get("estimated_time", "30-60秒"),
                    estimated_tokens=plan_data.get("estimated_tokens", 15000),
                    mode_recommendation=plan_data.get("mode_recommendation", "full"),
                )
            else:
                plan = self._default_plan()

        except Exception as e:
            logger.warning("Plan generation failed, using default: %s", e)
            plan = self._default_plan()

        # 通过 SSE 发送计划到前端
        if progress_callback:
            progress_callback({
                "type": "plan_ready",
                "plan": plan.to_dict(),
            })

        return plan

    def _default_plan(self) -> AnalysisPlan:
        """回退默认计划"""
        return AnalysisPlan(
            steps=list(_DEFAULT_PLAN_STEPS),
            estimated_time="30-60秒",
            estimated_tokens=15000,
            mode_recommendation="full",
        )
