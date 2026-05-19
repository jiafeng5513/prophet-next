# -*- coding: utf-8 -*-
"""
DebateCoordinator — 多轮 Bull/Bear 辩论协调器。

流程:
1. 并行执行 BullResearcher + BearResearcher（第 1 轮）
2. 将双方论据交叉注入对方上下文（第 2 轮反驳）
3. 多轮结束后，ResearchManager 做最终裁决
4. 将 ResearchPlan 写入 ctx.data["research_plan"]

辩论仅在 full / specialist 模式下启用。
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, Any, List, Optional, TYPE_CHECKING

from src.agent.agents.bull_researcher import BullResearcher
from src.agent.agents.bear_researcher import BearResearcher
from src.agent.agents.research_manager import ResearchManager
from src.agent.pipeline import PipelineStageGroup, execute_group_parallel

if TYPE_CHECKING:
    from src.agent.llm_adapter import LLMToolAdapter
    from src.agent.protocols import AgentContext, StageResult
    from src.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class DebateCoordinator:
    """协调 Bull/Bear 辩论 + ResearchManager 裁决。"""

    def __init__(
        self,
        tool_registry: "ToolRegistry",
        llm_adapter: "LLMToolAdapter",
        rounds: int = 2,
        max_workers: int = 2,
        timeout_seconds: Optional[float] = None,
    ):
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter
        self.rounds = max(1, rounds)
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

        # 创建子 Agent 实例
        self.bull = BullResearcher(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )
        self.bear = BearResearcher(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
        )
        self.manager = ResearchManager(
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
        执行完整辩论流程。

        Args:
            ctx: 共享上下文（已包含 Technical/Intel opinions）
            progress_callback: 进度回调
            run_stage_fn: 执行单个 agent 的函数签名 (agent, ctx, timeout) -> StageResult
                          若不提供则使用默认的 agent.run()

        Returns:
            所有 StageResult（bull rounds + bear rounds + manager）
        """
        if run_stage_fn is None:
            run_stage_fn = self._default_run_stage

        all_results: List["StageResult"] = []

        logger.info(
            "[Debate] Starting %d-round debate for %s",
            self.rounds, ctx.stock_code,
        )

        for round_idx in range(self.rounds):
            logger.info("[Debate] Round %d/%d", round_idx + 1, self.rounds)

            if progress_callback:
                progress_callback({
                    "stage": "debate",
                    "round": round_idx + 1,
                    "total_rounds": self.rounds,
                    "status": "running",
                })

            # Bull 和 Bear 并行执行
            group = PipelineStageGroup(
                agents=[self.bull, self.bear],
                parallel=True,
            )
            round_results = execute_group_parallel(
                group=group,
                ctx=ctx,
                run_stage_fn=run_stage_fn,
                timeout_seconds=self.timeout_seconds,
                max_workers=self.max_workers,
            )
            all_results.extend(round_results)

        # ResearchManager 裁决
        logger.info("[Debate] ResearchManager synthesizing verdict")
        if progress_callback:
            progress_callback({
                "stage": "debate",
                "status": "research_manager",
            })

        manager_result = run_stage_fn(self.manager, ctx, self.timeout_seconds)
        all_results.append(manager_result)

        logger.info("[Debate] Debate completed, research_plan set in ctx")
        return all_results

    @staticmethod
    def _default_run_stage(agent, ctx, timeout) -> "StageResult":
        """默认执行策略：直接调用 agent.run()"""
        return agent.run(ctx=ctx, timeout_seconds=timeout)
