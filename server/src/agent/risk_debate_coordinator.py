# -*- coding: utf-8 -*-
"""
RiskDebateCoordinator — 多视角风险讨论协调器。

流程:
1. 并行执行三个风险视角 Agent (Aggressive + Conservative + Neutral)
2. RiskDebateManager 综合三方视角做最终裁决
3. 将风险裁决写入 ctx.data["risk_debate_verdict"]

讨论仅在 full / specialist 模式下启用。
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Any, List, Optional, TYPE_CHECKING

from src.agent.agents.risk_debate import (
    AggressiveRiskAnalyst,
    ConservativeRiskAnalyst,
    NeutralRiskAnalyst,
    RiskDebateManager,
)
from src.agent.pipeline import PipelineStageGroup, execute_group_parallel

if TYPE_CHECKING:
    from src.agent.llm_adapter import LLMToolAdapter
    from src.agent.protocols import AgentContext, StageResult
    from src.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class RiskDebateCoordinator:
    """协调三视角风险讨论 + RiskManager 裁决。"""

    def __init__(
        self,
        tool_registry: "ToolRegistry",
        llm_adapter: "LLMToolAdapter",
        max_workers: int = 3,
        timeout_seconds: Optional[float] = None,
    ):
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

        # 创建子 Agent 实例
        self.aggressive = AggressiveRiskAnalyst(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )
        self.conservative = ConservativeRiskAnalyst(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )
        self.neutral = NeutralRiskAnalyst(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )
        self.manager = RiskDebateManager(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )

    def run(
        self,
        ctx: "AgentContext",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        run_stage_fn: Optional[Callable] = None,
    ) -> List["StageResult"]:
        """
        执行完整风险讨论流程。

        Args:
            ctx: 共享上下文（已包含 opinions + research_plan）
            progress_callback: 进度回调
            run_stage_fn: 执行单个 agent 的函数

        Returns:
            所有 StageResult（3 perspectives + manager）
        """
        if run_stage_fn is None:
            run_stage_fn = self._default_run_stage

        all_results: List["StageResult"] = []

        logger.info("[RiskDebate] Starting 3-perspective risk discussion for %s", ctx.stock_code)

        if progress_callback:
            progress_callback({
                "type": "risk_debate",
                "stage": "risk_debate",
                "status": "running",
                "perspectives": ["aggressive", "conservative", "neutral"],
            })

        # 三个视角并行执行
        group = PipelineStageGroup(
            agents=[self.aggressive, self.conservative, self.neutral],
            parallel=True,
        )
        perspective_results = execute_group_parallel(
            group=group,
            ctx=ctx,
            run_stage_fn=run_stage_fn,
            timeout_seconds=self.timeout_seconds,
            max_workers=self.max_workers,
        )
        all_results.extend(perspective_results)

        # RiskManager 综合裁决
        logger.info("[RiskDebate] RiskManager synthesizing verdict")
        if progress_callback:
            progress_callback({
                "type": "risk_debate",
                "stage": "risk_debate",
                "status": "completed",
            })

        manager_result = run_stage_fn(self.manager, ctx, self.timeout_seconds)
        all_results.append(manager_result)

        logger.info("[RiskDebate] Risk debate completed, verdict set in ctx")
        return all_results

    @staticmethod
    def _default_run_stage(agent, ctx, timeout) -> "StageResult":
        """默认执行策略：直接调用 agent.run()"""
        return agent.run(ctx=ctx, timeout_seconds=timeout)
