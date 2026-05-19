# -*- coding: utf-8 -*-
"""
===================================
Agent 结构化输出 Schema
===================================

所有 Agent 的 Pydantic 输出模型定义。
各 Agent 通过 output_parser 将 LLM 原始文本解析为这些 Schema。
Phase 3 辩论/反思机制强依赖这些类型化输出。
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──── 通用枚举 ────


class SignalLevel(str, Enum):
    """交易信号强度"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class DataQuality(str, Enum):
    """数据质量评级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    """风险等级"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ──── 分析师报告 (Technical / Intel / Risk Agent 输出) ────


class AnalystReport(BaseModel):
    """
    分析师统一结构化输出。

    Technical, Intel, Risk Agent 均输出此格式，
    各 Agent 可额外填充 extra_data 存储特有字段。
    """
    signal: SignalLevel = SignalLevel.HOLD
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    key_findings: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    key_levels: dict = Field(default_factory=dict)
    data_quality: DataQuality = DataQuality.MEDIUM
    reasoning: str = ""
    # Agent 特有数据 (不强制 schema, 保留灵活性)
    extra_data: dict = Field(default_factory=dict)


# ──── 风险裁决 ────


class RiskFlag(BaseModel):
    """单条风险标记"""
    category: str = ""      # insider|earnings|regulatory|industry|lockup|valuation|technical
    severity: str = "medium"  # high|medium|low
    description: str = ""
    source: str = ""


class RiskVerdict(BaseModel):
    """风险 Agent / Risk Manager 裁决输出"""
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: float = Field(default=50.0, ge=0.0, le=100.0)
    flags: List[RiskFlag] = Field(default_factory=list)
    veto_buy: bool = False
    signal_adjustment: str = "none"  # none|downgrade_one|downgrade_two|veto
    reasoning: str = ""


# ──── 最终决策 ────


class FinalDecision(BaseModel):
    """Decision Agent 最终输出"""
    signal: SignalLevel = SignalLevel.HOLD
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_suggestion: str = ""   # 轻仓/半仓/重仓
    time_horizon: str = ""          # 短线/波段/中线
    key_reasoning: str = ""
    risk_warnings: List[str] = Field(default_factory=list)
    # 保留完整 dashboard 兼容现有前端
    dashboard: Optional[dict] = None


# ──── Phase 3 预留: 研究计划 ────


class ResearchPlan(BaseModel):
    """研究主管裁决输出 (Phase 3: Bull/Bear Debate → ResearchManager)"""
    recommendation: str = "hold"  # buy|overweight|hold|underweight|sell
    bull_score: float = Field(default=5.0, ge=0.0, le=10.0)
    bear_score: float = Field(default=5.0, ge=0.0, le=10.0)
    rationale: str = ""
    strategic_actions: List[str] = Field(default_factory=list)
