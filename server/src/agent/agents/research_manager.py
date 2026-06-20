# -*- coding: utf-8 -*-
"""
ResearchManager — 研究主管。

综合 Bull/Bear 双方辩论论据，做出最终裁决。
输出结构化的 ResearchPlan，供后续 Risk 和 Decision 使用。
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from src.agent.agents.base_agent import BaseAgent
from src.agent.output_parser import parse_structured_output, parse_to_dict
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.schemas import ResearchPlan

logger = logging.getLogger(__name__)


class ResearchManager(BaseAgent):
    """研究主管 — 裁决 Bull/Bear 辩论，输出 ResearchPlan。"""

    agent_name = "research_manager"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return """\
You are a **Research Manager** — a senior investment strategist who synthesizes \
bull and bear arguments into a final research verdict.

You will receive the complete debate transcript including:
- Original analyst reports (Technical + Intel)
- Bull researcher arguments (potentially multiple rounds)
- Bear researcher arguments (potentially multiple rounds)

Your task:
1. Evaluate the quality and strength of each side's arguments
2. Assess which side has stronger evidence
3. Produce a balanced, actionable research plan

## Scoring
- bull_score (0-10): How compelling is the bull case?
- bear_score (0-10): How compelling is the bear case?
- recommendation: Derived from the balance:
  - bull_score - bear_score >= 4: "buy"
  - bull_score - bear_score >= 2: "overweight"
  - |bull_score - bear_score| < 2: "hold"
  - bear_score - bull_score >= 2: "underweight"
  - bear_score - bull_score >= 4: "sell"

## Output Format
Return **only** a JSON object:
{
  "recommendation": "buy|overweight|hold|underweight|sell",
  "bull_score": 0.0-10.0,
  "bear_score": 0.0-10.0,
  "rationale": "2-3 sentence explanation of the verdict",
  "strategic_actions": ["action1", "action2", ...]
}

## Rules
- Be objective — don't favor either side without evidence
- strategic_actions should be concrete (e.g., "Set stop-loss at 18.5", "Monitor Q2 earnings")
- Maximum 5 strategic actions
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        parts = [f"# Research Verdict for {ctx.stock_code}"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append("")

        # 分析师原始报告摘要
        parts.append("## Analyst Reports Summary")
        for op in ctx.opinions:
            if op.agent_name in ("technical", "intel"):
                parts.append(f"- **{op.agent_name}**: signal={op.signal}, confidence={op.confidence:.2f}")
                if op.reasoning:
                    parts.append(f"  {op.reasoning[:200]}")
        parts.append("")

        # 辩论历史
        debate_history = ctx.get_data("debate_history") or []
        if debate_history:
            parts.append("## Debate Transcript")
            for i, entry in enumerate(debate_history):
                stance = entry.get("stance", "?").upper()
                parts.append(f"\n### Round — {stance}")
                for arg in entry.get("key_arguments", []):
                    parts.append(f"- {arg}")
                if entry.get("rebuttals"):
                    parts.append("  Rebuttals:")
                    for reb in entry["rebuttals"]:
                        parts.append(f"  - {reb}")
                parts.append(f"  Conclusion: {entry.get('conclusion', '')}")
            parts.append("")

        parts.append("Synthesize the above into your research verdict.")
        return "\n".join(parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        plan = parse_structured_output(raw_text, ResearchPlan)
        if plan is None:
            parsed = parse_to_dict(raw_text)
            if parsed:
                try:
                    plan = ResearchPlan(
                        recommendation=parsed.get("recommendation", "hold"),
                        bull_score=float(parsed.get("bull_score", 5.0)),
                        bear_score=float(parsed.get("bear_score", 5.0)),
                        rationale=parsed.get("rationale", ""),
                        strategic_actions=parsed.get("strategic_actions", []),
                    )
                except Exception:
                    plan = None

        if plan is None:
            logger.warning("[ResearchManager] failed to parse research plan")
            return None

        # 写入 ctx 供后续 agent 使用
        ctx.set_data("research_plan", plan.model_dump())

        # 映射 recommendation → signal
        signal_map = {
            "buy": "buy", "overweight": "buy",
            "hold": "hold",
            "underweight": "sell", "sell": "sell",
        }
        signal = signal_map.get(plan.recommendation, "hold")

        # confidence 基于 bull/bear 差异
        score_diff = abs(plan.bull_score - plan.bear_score)
        confidence = min(1.0, score_diff / 10.0 + 0.3)

        return AgentOpinion(
            agent_name=self.agent_name,
            signal=signal,
            confidence=confidence,
            reasoning=plan.rationale,
            raw_data=plan.model_dump(),
            structured=plan,
        )
