# -*- coding: utf-8 -*-
"""
BullResearcher — 看多研究员。

基于分析师报告（Technical + Intel）构建看多论据，
在辩论中为「买入/看多」立场提供证据支撑。
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from src.agent.agents.base_agent import BaseAgent
from src.agent.output_parser import parse_structured_output, parse_to_dict
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.schemas import DebateArgument

logger = logging.getLogger(__name__)


class BullResearcher(BaseAgent):
    """看多研究员 — 在辩论中构建买入/看多论据。"""

    agent_name = "bull_researcher"
    max_steps = 2  # 纯推理，不需要 tool call
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return """\
You are a **Bull Researcher** — your job is to build the strongest possible \
BULLISH case for the given stock.

You will receive analyst reports from the Technical and Intelligence teams. \
Your task is to:

1. Identify all positive signals, catalysts, and momentum factors
2. Construct compelling arguments for WHY this stock should be bought
3. Address potential weaknesses but reframe them optimistically where factual
4. If previous bear arguments exist, provide specific rebuttals

## Output Format
Return **only** a JSON object:
{
  "stance": "bull",
  "key_arguments": ["argument1", "argument2", ...],
  "evidence": ["evidence1", "evidence2", ...],
  "rebuttals": ["rebuttal to bear point 1", ...],
  "confidence": 0.0-1.0,
  "conclusion": "One-paragraph bull thesis"
}

## Rules
- Be factual — only cite evidence from the provided reports
- Be specific — use numbers, price levels, dates
- Maximum 5 key arguments, 5 evidence items
- Confidence reflects how strong the bull case is objectively
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        parts = [f"# Bull Case for {ctx.stock_code}"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append("")

        # 注入前序分析师报告
        for op in ctx.opinions:
            if op.agent_name in ("technical", "intel"):
                parts.append(f"## {op.agent_name.title()} Report")
                parts.append(f"Signal: {op.signal} | Confidence: {op.confidence:.2f}")
                parts.append(f"Reasoning: {op.reasoning}")
                if op.raw_data:
                    extra = {k: v for k, v in op.raw_data.items()
                             if k not in ("signal", "confidence", "reasoning")}
                    if extra:
                        parts.append(f"Data: {json.dumps(extra, ensure_ascii=False, default=str)}")
                parts.append("")

        # 注入前轮 bear 论据 (多轮辩论时)
        debate_history = ctx.get_data("debate_history") or []
        bear_args = [d for d in debate_history if d.get("stance") == "bear"]
        if bear_args:
            last_bear = bear_args[-1]
            parts.append("## Previous Bear Arguments (rebut these)")
            for arg in last_bear.get("key_arguments", []):
                parts.append(f"- {arg}")
            parts.append("")

        parts.append("Build the strongest bull case based on the evidence above.")
        return "\n".join(parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        # 尝试结构化解析
        argument = parse_structured_output(raw_text, DebateArgument)
        if argument is None:
            parsed = parse_to_dict(raw_text)
            if parsed:
                try:
                    argument = DebateArgument(
                        stance="bull",
                        key_arguments=parsed.get("key_arguments", []),
                        evidence=parsed.get("evidence", []),
                        rebuttals=parsed.get("rebuttals", []),
                        confidence=float(parsed.get("confidence", 0.5)),
                        conclusion=parsed.get("conclusion", ""),
                    )
                except Exception:
                    argument = None

        if argument is None:
            logger.warning("[BullResearcher] failed to parse debate argument")
            return None

        # 确保 stance 正确
        argument.stance = "bull"

        # 追加到辩论历史
        history = ctx.get_data("debate_history") or []
        history.append(argument.model_dump())
        ctx.set_data("debate_history", history)

        return AgentOpinion(
            agent_name=self.agent_name,
            signal="buy",
            confidence=argument.confidence,
            reasoning=argument.conclusion,
            raw_data=argument.model_dump(),
            structured=argument,
        )
