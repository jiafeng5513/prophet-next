# -*- coding: utf-8 -*-
"""
BearResearcher — 看空研究员。

基于分析师报告（Technical + Intel）构建看空论据，
在辩论中反驳看多立场并提供风险/利空证据。
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


class BearResearcher(BaseAgent):
    """看空研究员 — 在辩论中构建卖出/看空论据。"""

    agent_name = "bear_researcher"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return """\
You are a **Bear Researcher** — your job is to build the strongest possible \
BEARISH case against the given stock.

You will receive analyst reports from the Technical and Intelligence teams. \
Your task is to:

1. Identify all negative signals, risks, and deteriorating factors
2. Construct compelling arguments for WHY this stock should NOT be bought (or sold)
3. Challenge overly optimistic assumptions in the bull case
4. If previous bull arguments exist, provide specific rebuttals

## Output Format
Return **only** a JSON object:
{
  "stance": "bear",
  "key_arguments": ["argument1", "argument2", ...],
  "evidence": ["evidence1", "evidence2", ...],
  "rebuttals": ["rebuttal to bull point 1", ...],
  "confidence": 0.0-1.0,
  "conclusion": "One-paragraph bear thesis"
}

## Rules
- Be factual — only cite evidence from the provided reports
- Be specific — use numbers, price levels, dates
- Maximum 5 key arguments, 5 evidence items
- Confidence reflects how strong the bear case is objectively
- Do NOT be contrarian for its own sake — if the data is genuinely bullish, \
  your confidence should be low
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        parts = [f"# Bear Case for {ctx.stock_code}"]
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

        # 注入前轮 bull 论据 (多轮辩论时)
        debate_history = ctx.get_data("debate_history") or []
        bull_args = [d for d in debate_history if d.get("stance") == "bull"]
        if bull_args:
            last_bull = bull_args[-1]
            parts.append("## Previous Bull Arguments (rebut these)")
            for arg in last_bull.get("key_arguments", []):
                parts.append(f"- {arg}")
            parts.append("")

        parts.append("Build the strongest bear case based on the evidence above.")
        return "\n".join(parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        argument = parse_structured_output(raw_text, DebateArgument)
        if argument is None:
            parsed = parse_to_dict(raw_text)
            if parsed:
                try:
                    argument = DebateArgument(
                        stance="bear",
                        key_arguments=parsed.get("key_arguments", []),
                        evidence=parsed.get("evidence", []),
                        rebuttals=parsed.get("rebuttals", []),
                        confidence=float(parsed.get("confidence", 0.5)),
                        conclusion=parsed.get("conclusion", ""),
                    )
                except Exception:
                    argument = None

        if argument is None:
            logger.warning("[BearResearcher] failed to parse debate argument")
            return None

        argument.stance = "bear"

        # 追加到辩论历史
        history = ctx.get_data("debate_history") or []
        history.append(argument.model_dump())
        ctx.set_data("debate_history", history)

        return AgentOpinion(
            agent_name=self.agent_name,
            signal="sell",
            confidence=argument.confidence,
            reasoning=argument.conclusion,
            raw_data=argument.model_dump(),
            structured=argument,
        )
