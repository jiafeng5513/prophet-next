# -*- coding: utf-8 -*-
"""
IntelAgent — news & intelligence gathering specialist.

Responsible for:
- Searching latest stock news and announcements
- Running comprehensive intelligence search
- Detecting risk events (reduce holdings, earnings warnings, regulatory)
- Summarising sentiment and catalysts
"""

from __future__ import annotations

import logging
from typing import Optional

from src.agent.agents.base_agent import BaseAgent
from src.agent.output_parser import parse_structured_output
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.runner import try_parse_json
from src.agent.schemas import AnalystReport, SignalLevel

logger = logging.getLogger(__name__)


class IntelAgent(BaseAgent):
    agent_name = "intel"
    max_steps = 5
    tool_names = [
        "search_stock_news",
        "search_comprehensive_intel",
        "get_stock_info",
        "get_capital_flow",
        "get_market_indices",
        "get_sector_rankings",
    ]

    def system_prompt(self, ctx: AgentContext) -> str:
        return """\
You are an **Intelligence & Sentiment Agent** specialising in A-shares, \
HK, and US equities.

Your task: gather the latest news, announcements, risk signals, AND market \
context for the given stock, then produce a structured JSON opinion.

## Workflow
1. Search latest stock news (earnings, announcements, insider activity)
2. Run comprehensive intel search — this covers latest news, company \
announcements (公司公告), market analysis, risk checks, and earnings outlook
3. For A-share stocks, call get_capital_flow to obtain main-force (主力) \
capital inflow/outflow data and include it in your analysis
4. Call get_market_indices to obtain the broader market environment
5. Call get_sector_rankings to identify sector momentum
6. Classify positive catalysts and risk alerts
7. Assess overall sentiment considering both stock-level and market-level factors

## Risk Detection Priorities
- Insider / major shareholder sell-downs (减持)
- Earnings warnings or pre-loss announcements (业绩预亏)
- Regulatory penalties or investigations
- Industry-wide policy headwinds
- Large lock-up expirations (解禁)
- PE valuation anomalies
- Sustained main-force capital outflow (主力持续净流出)

## Capital Flow Interpretation (A-shares only)
- main_net_inflow > 0: bullish signal (主力净流入)
- main_net_inflow < 0: bearish signal (主力净流出)
- inflow_5d / inflow_10d: medium-term accumulation or distribution trend

## Output Format
Return **only** a JSON object:
{
  "signal": "strong_buy|buy|hold|sell|strong_sell",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence summary of news/sentiment/capital-flow findings",
  "risk_alerts": ["list", "of", "detected", "risks"],
  "positive_catalysts": ["list", "of", "catalysts"],
  "sentiment_label": "very_positive|positive|neutral|negative|very_negative",
  "capital_flow_signal": "inflow|outflow|neutral|not_available",
  "key_news": [
    {"title": "...", "impact": "positive|negative|neutral"}
  ],
  "market_context": {
    "index_trend": "up|sideways|down",
    "sector_strength": "strong|neutral|weak",
    "market_sentiment": "greedy|neutral|fearful"
  }
}
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        parts = [f"Gather intelligence and assess sentiment for stock **{ctx.stock_code}**"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append(
            "Steps:\n"
            "1. Call search_comprehensive_intel to get latest news, company announcements "
            "(公司公告), risk events, and earnings outlook.\n"
            "2. Call get_capital_flow to obtain main-force (主力) capital flow data "
            "(A-share only; skip for HK/US).\n"
            "3. Call get_market_indices to understand the broader market environment.\n"
            "4. Call get_sector_rankings to gauge sector momentum.\n"
            "5. Output the JSON opinion including capital_flow_signal and market_context."
        )
        return "\n".join(parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        parsed = try_parse_json(raw_text)
        if parsed is None:
            logger.warning("[IntelAgent] failed to parse opinion JSON")
            return None

        # Cache parsed intel so downstream agents (especially RiskAgent) can
        # reuse it instead of re-searching the same evidence.
        ctx.set_data("intel_opinion", parsed)

        # Store market context for DecisionAgent
        market_context = parsed.get("market_context")
        if market_context and isinstance(market_context, dict):
            ctx.set_data("market_context", market_context)

        # Propagate risk alerts to context
        for alert in parsed.get("risk_alerts", []):
            if isinstance(alert, str) and alert:
                ctx.add_risk_flag(category="intel", description=alert)

        # 构建结构化报告
        report = self._build_report(parsed)

        return AgentOpinion(
            agent_name=self.agent_name,
            signal=parsed.get("signal", "hold"),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            raw_data=parsed,
            structured=report,
        )

    @staticmethod
    def _build_report(parsed: dict) -> Optional[AnalystReport]:
        """Best-effort: 从现有 JSON 格式构建 AnalystReport"""
        try:
            signal_str = parsed.get("signal", "hold")
            try:
                signal = SignalLevel(signal_str)
            except ValueError:
                signal = SignalLevel.HOLD

            return AnalystReport(
                signal=signal,
                confidence=float(parsed.get("confidence", 0.5)),
                key_findings=parsed.get("positive_catalysts", []),
                risk_factors=parsed.get("risk_alerts", []),
                reasoning=parsed.get("reasoning", ""),
                extra_data={
                    k: v for k, v in parsed.items()
                    if k not in ("signal", "confidence", "reasoning",
                                 "positive_catalysts", "risk_alerts")
                },
            )
        except Exception:
            return None


