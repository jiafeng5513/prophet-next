# -*- coding: utf-8 -*-
"""
===================================
Pipeline 并行分组执行
===================================

将 Agent 管线按依赖关系分组:
- 同一组内的 Agent 可并行执行 (无数据依赖)
- 组间严格按序执行

默认分组:
- Group 1: [technical, intel]  — 并行，无互相依赖
- Group 2: [risk]             — 依赖 intel 的 risk_alerts
- Group 3: [decision]         — 依赖所有前序 opinions

Specialist (skill) agents 在 Group 2 和 Group 3 之间插入，与 risk 并行或串行取决于配置。
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.agents.base_agent import BaseAgent
    from src.agent.protocols import AgentContext, StageResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageGroup:
    """一组可并行执行的 Agent。"""
    agents: List["BaseAgent"] = field(default_factory=list)
    parallel: bool = False  # True = 组内并行; False = 组内串行


def build_parallel_groups(
    agents: List["BaseAgent"],
    enable_parallel: bool = True,
) -> List[PipelineStageGroup]:
    """
    将 agent 列表按依赖关系划分为执行组。

    规则:
    - technical 和 intel 放入同一组且标记 parallel
    - risk 单独一组 (依赖 intel 输出)
    - decision 单独一组 (依赖所有前序)
    - 其他 agent (skill) 单独一组或按照插入顺序串行

    如果 enable_parallel=False，所有组都标记为串行 (兼容模式)。
    """
    if not enable_parallel:
        # 兼容模式: 每个 agent 一个串行组
        return [PipelineStageGroup(agents=[a], parallel=False) for a in agents]

    # 分类
    parallel_candidates = {"technical", "intel"}
    sequential_after = {"risk", "decision"}

    parallel_group: List["BaseAgent"] = []
    rest: List["BaseAgent"] = []

    for agent in agents:
        if agent.agent_name in parallel_candidates:
            parallel_group.append(agent)
        else:
            rest.append(agent)

    groups: List[PipelineStageGroup] = []

    # Group 1: 并行 (technical + intel)
    if parallel_group:
        groups.append(PipelineStageGroup(
            agents=parallel_group,
            parallel=len(parallel_group) > 1,
        ))

    # 剩余 agents 各自成组 (串行)
    for agent in rest:
        groups.append(PipelineStageGroup(agents=[agent], parallel=False))

    return groups


def execute_group_parallel(
    group: PipelineStageGroup,
    ctx: "AgentContext",
    run_stage_fn: Callable[["BaseAgent", "AgentContext", Optional[float]], "StageResult"],
    timeout_seconds: Optional[float] = None,
    max_workers: int = 3,
) -> List["StageResult"]:
    """
    执行一个 PipelineStageGroup 中的所有 agent。

    如果 group.parallel=True，使用 ThreadPoolExecutor 并行。
    否则串行执行。

    Args:
        group: 要执行的组
        ctx: 共享上下文 (并行执行时需要线程安全)
        run_stage_fn: 执行单个 agent 的函数 (agent, ctx, timeout) -> StageResult
        timeout_seconds: 整组超时
        max_workers: 并行时最大线程数

    Returns:
        StageResult 列表 (与 group.agents 顺序对应)
    """
    if not group.agents:
        return []

    if not group.parallel or len(group.agents) == 1:
        # 串行执行
        results = []
        for agent in group.agents:
            result = run_stage_fn(agent, ctx, timeout_seconds)
            results.append(result)
        return results

    # 并行执行
    results: List[Optional["StageResult"]] = [None] * len(group.agents)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(group.agents))) as executor:
        future_to_idx = {
            executor.submit(run_stage_fn, agent, ctx, timeout_seconds): idx
            for idx, agent in enumerate(group.agents)
        }

        for future in as_completed(future_to_idx, timeout=timeout_seconds):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(
                    "[Pipeline] parallel agent '%s' raised: %s",
                    group.agents[idx].agent_name, e,
                )
                # 创建一个失败的 StageResult
                from src.agent.protocols import StageResult, StageStatus
                results[idx] = StageResult(
                    agent_name=group.agents[idx].agent_name,
                    status=StageStatus.FAILED,
                    error=str(e),
                    duration_s=0.0,
                )

    # 填充未完成的 (超时)
    from src.agent.protocols import StageResult, StageStatus
    for idx, r in enumerate(results):
        if r is None:
            results[idx] = StageResult(
                agent_name=group.agents[idx].agent_name,
                status=StageStatus.FAILED,
                error="Timed out in parallel execution",
                duration_s=timeout_seconds or 0.0,
            )

    return results  # type: ignore[return-value]
