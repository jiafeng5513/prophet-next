# -*- coding: utf-8 -*-
"""
多视角风险分析师 + 风险主管。

三种视角:
- AggressiveRiskAnalyst: 激进型，聚焦机会成本、错过的收益
- ConservativeRiskAnalyst: 保守型，聚焦下行风险、资本保全
- NeutralRiskAnalyst: 中性型，概率加权分析

RiskManager: 综合三方视角做最终风险裁决。
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from src.agent.agents.base_agent import BaseAgent
from src.agent.output_parser import parse_structured_output, parse_to_dict
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.schemas import RiskPerspective

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Base Risk Analyst (shared prompt structure)
# ──────────────────────────────────────────────────────────────────────

_RISK_OUTPUT_FORMAT = """\
## Output Format
Return **only** a JSON object:
{
  "perspective": "<your_perspective>",
  "risk_assessment": "Overall risk summary",
  "position_recommendation": "e.g. 80% position / 30% position / no position",
  "key_concerns": ["concern1", ...],
  "opportunities_missed": ["opportunity1 if too cautious", ...],
  "worst_case_scenario": "What's the worst that could happen",
  "probability_weighted_outcome": "Expected outcome with probabilities",
  "overall_risk_score": 0-100
}

## Rules
- overall_risk_score: 0 = no risk at all, 100 = extreme risk
- Maximum 5 key_concerns, 3 opportunities_missed
- Be specific: cite numbers, price levels, timeframes
"""


class AggressiveRiskAnalyst(BaseAgent):
    """激进型风险分析师 — 聚焦机会成本和错过收益。"""

    agent_name = "risk_aggressive"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""\
You are an **Aggressive Risk Analyst** — your philosophy is that \
NOT taking action is itself a risk. You focus on:

1. Opportunity cost of NOT entering/holding the position
2. Missed upside due to overcautious risk management
3. Whether the market has already priced in obvious risks
4. Growth potential that justifies higher risk tolerance

Your risk_score tends LOWER (you see less risk) because you believe \
most "risks" are already priced in or overblown.

{_RISK_OUTPUT_FORMAT}
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        return _build_risk_user_message(ctx, "aggressive")

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        return _parse_risk_perspective(self.agent_name, "aggressive", ctx, raw_text)


class ConservativeRiskAnalyst(BaseAgent):
    """保守型风险分析师 — 聚焦下行保护和资本保全。"""

    agent_name = "risk_conservative"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""\
You are a **Conservative Risk Analyst** — your philosophy is that \
capital preservation is paramount. You focus on:

1. Downside scenarios and how bad they could get
2. Black swan events and tail risks specific to this stock/sector
3. Liquidity risk — can you exit when you need to?
4. Correlation risk — does this add to existing portfolio concentration?
5. Whether stop-losses and risk limits are adequate

Your risk_score tends HIGHER (you see more risk) because you believe \
markets systematically underestimate tail events.

{_RISK_OUTPUT_FORMAT}
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        return _build_risk_user_message(ctx, "conservative")

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        return _parse_risk_perspective(self.agent_name, "conservative", ctx, raw_text)


class NeutralRiskAnalyst(BaseAgent):
    """中性风险分析师 — 概率加权客观评估。"""

    agent_name = "risk_neutral"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""\
You are a **Neutral Risk Analyst** — your philosophy is pure \
probability-weighted analysis without emotional bias. You focus on:

1. Base rates — what % of similar setups historically succeed?
2. Expected value calculation (probability × magnitude for each scenario)
3. Risk-reward ratio objectivity
4. Position sizing based on Kelly criterion principles
5. Correlation with broader market regime

Your risk_score is calibrated to historical averages — you are neither \
systematically high nor low.

{_RISK_OUTPUT_FORMAT}
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        return _build_risk_user_message(ctx, "neutral")

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        return _parse_risk_perspective(self.agent_name, "neutral", ctx, raw_text)


# ──────────────────────────────────────────────────────────────────────
# RiskManager — 综合裁决
# ──────────────────────────────────────────────────────────────────────


class RiskDebateManager(BaseAgent):
    """风险主管 — 综合三视角得出最终风险评级。"""

    agent_name = "risk_manager"
    max_steps = 2
    tool_names: Optional[List[str]] = []

    def system_prompt(self, ctx: AgentContext) -> str:
        return """\
You are a **Risk Manager** — you synthesize assessments from three \
risk analysts (Aggressive, Conservative, Neutral) into a final risk verdict.

You will receive three risk perspectives. Your task:
1. Weigh each perspective based on the current market regime
2. Identify consensus risks (mentioned by 2+ analysts)
3. Determine the appropriate position size recommendation
4. Set a final risk level

## Output Format
Return **only** a JSON object:
{
  "final_risk_level": "low|medium|high|critical",
  "consensus_risks": ["risk mentioned by multiple analysts", ...],
  "position_size_pct": 0-100,
  "rationale": "2-3 sentence explanation",
  "risk_adjusted_action": "buy_full|buy_half|hold|reduce|exit"
}

## Rules
- position_size_pct: recommended allocation (100=full, 0=none)
- If any analyst flags "critical", you must acknowledge it even if others disagree
- Be specific in rationale — cite which perspectives you weighted more and why
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        parts = [f"# Risk Synthesis for {ctx.stock_code}"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append("")

        # 注入三个视角
        risk_perspectives = ctx.get_data("risk_perspectives") or []
        for p in risk_perspectives:
            perspective = p.get("perspective", "?").upper()
            parts.append(f"## {perspective} Perspective")
            parts.append(f"Risk Score: {p.get('overall_risk_score', '?')}/100")
            parts.append(f"Assessment: {p.get('risk_assessment', '')}")
            parts.append(f"Position: {p.get('position_recommendation', '')}")
            if p.get("key_concerns"):
                parts.append("Concerns:")
                for c in p["key_concerns"]:
                    parts.append(f"  - {c}")
            if p.get("opportunities_missed"):
                parts.append("Missed opportunities:")
                for o in p["opportunities_missed"]:
                    parts.append(f"  - {o}")
            parts.append(f"Worst case: {p.get('worst_case_scenario', '')}")
            parts.append("")

        # 注入 research plan (辩论结果)
        research_plan = ctx.get_data("research_plan")
        if research_plan:
            parts.append("## Research Plan Context")
            parts.append(f"Recommendation: {research_plan.get('recommendation', '?')}")
            parts.append(f"Bull/Bear scores: {research_plan.get('bull_score', '?')}/{research_plan.get('bear_score', '?')}")
            parts.append("")

        parts.append("Synthesize the above into your final risk verdict.")
        return "\n".join(parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        parsed = parse_to_dict(raw_text)
        if not parsed:
            logger.warning("[RiskManager] failed to parse risk verdict")
            return None

        final_level = parsed.get("final_risk_level", "medium")
        position_pct = float(parsed.get("position_size_pct", 50))
        rationale = parsed.get("rationale", "")
        action = parsed.get("risk_adjusted_action", "hold")

        # 写入 ctx
        ctx.set_data("risk_debate_verdict", parsed)

        # 映射 action → signal
        action_signal_map = {
            "buy_full": "buy",
            "buy_half": "buy",
            "hold": "hold",
            "reduce": "sell",
            "exit": "sell",
        }
        signal = action_signal_map.get(action, "hold")

        # confidence 反转 risk_score 概念
        confidence = position_pct / 100.0

        return AgentOpinion(
            agent_name=self.agent_name,
            signal=signal,
            confidence=confidence,
            reasoning=rationale,
            raw_data=parsed,
        )


# ──────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────


def _build_risk_user_message(ctx: "AgentContext", perspective: str) -> str:
    """构建风险分析师的 user message (三个视角共用结构)。"""
    parts = [f"# {perspective.title()} Risk Analysis for {ctx.stock_code}"]
    if ctx.stock_name:
        parts[0] += f" ({ctx.stock_name})"
    parts.append("")

    # 前序 opinions 摘要
    for op in ctx.opinions:
        if op.agent_name in ("technical", "intel", "research_manager"):
            parts.append(f"## {op.agent_name.title()} Summary")
            parts.append(f"Signal: {op.signal} | Confidence: {op.confidence:.2f}")
            parts.append(f"Reasoning: {op.reasoning[:300] if op.reasoning else ''}")
            parts.append("")

    # research plan 上下文
    research_plan = ctx.get_data("research_plan")
    if research_plan:
        parts.append("## Research Plan")
        parts.append(f"Recommendation: {research_plan.get('recommendation', '?')}")
        parts.append(f"Bull/Bear: {research_plan.get('bull_score', '?')}/{research_plan.get('bear_score', '?')}")
        parts.append(f"Rationale: {research_plan.get('rationale', '')}")
        parts.append("")

    parts.append(f"Provide your {perspective} risk perspective.")
    return "\n".join(parts)


def _parse_risk_perspective(
    agent_name: str,
    perspective: str,
    ctx: "AgentContext",
    raw_text: str,
) -> Optional[AgentOpinion]:
    """解析风险视角输出并追加到 ctx 的 risk_perspectives 列表。"""
    rp = parse_structured_output(raw_text, RiskPerspective)
    if rp is None:
        parsed = parse_to_dict(raw_text)
        if parsed:
            try:
                rp = RiskPerspective(
                    perspective=perspective,
                    risk_assessment=parsed.get("risk_assessment", ""),
                    position_recommendation=parsed.get("position_recommendation", ""),
                    key_concerns=parsed.get("key_concerns", []),
                    opportunities_missed=parsed.get("opportunities_missed", []),
                    worst_case_scenario=parsed.get("worst_case_scenario", ""),
                    probability_weighted_outcome=parsed.get("probability_weighted_outcome", ""),
                    overall_risk_score=float(parsed.get("overall_risk_score", 50.0)),
                )
            except Exception:
                rp = None

    if rp is None:
        logger.warning("[%s] failed to parse risk perspective", agent_name)
        return None

    rp.perspective = perspective

    # 追加到 risk_perspectives
    perspectives = ctx.get_data("risk_perspectives") or []
    perspectives.append(rp.model_dump())
    ctx.set_data("risk_perspectives", perspectives)

    # 映射 risk_score → signal
    score = rp.overall_risk_score
    if score >= 75:
        signal = "sell"
    elif score >= 50:
        signal = "hold"
    else:
        signal = "buy"

    confidence = 1.0 - (score / 100.0)

    return AgentOpinion(
        agent_name=agent_name,
        signal=signal,
        confidence=confidence,
        reasoning=rp.risk_assessment,
        raw_data=rp.model_dump(),
        structured=rp,
    )
