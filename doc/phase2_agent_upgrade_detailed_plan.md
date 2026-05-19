# Phase 2 — 智能体核心升级（详细开发计划）

> 目标：在现有串行 Orchestrator 基础上，引入双层 LLM 调度、结构化输出 Schema、DAG 并行执行，为 Phase 3 的辩论/反思机制奠定基础。

---

## 目录
1. [现状分析与差距](#现状分析与差距)
2. [E1: 双层 LLM 分级调度](#e1-双层-llm-分级调度)
3. [E5: 结构化输出 Schema](#e5-结构化输出-schema)
4. [E6: 并行执行优化](#e6-并行执行优化)
5. [开发时间线与优先级](#开发时间线与优先级)
6. [技术决策与风险](#技术决策与风险)

---

## 现状分析与差距

### 已有基础

| 组件 | 文件 | 现状 |
|------|------|------|
| AgentOrchestrator | `src/agent/orchestrator.py` | 串行状态机, quick/standard/full/specialist 四模式 |
| LLMToolAdapter | `src/agent/llm_adapter.py` | 单主模型 + fallback 链, LiteLLM Router 负载均衡 |
| AgentOpinion | `src/agent/protocols.py` | dataclass: signal/confidence/reasoning/key_levels/raw_data |
| StageResult | `src/agent/protocols.py` | 阶段执行结果, 含 status/duration/tokens |
| 工具并行 | `src/agent/runner.py` | 同一 Agent 内的 tool_calls 用 ThreadPoolExecutor 并行 |
| 超时管理 | orchestrator.py | 协作式预算 (cooperative budget), 阶段最低保底 |
| 风险否决 | orchestrator.py | `_apply_risk_override()` — risk agent 可将 buy→hold |

### 核心差距

| # | 差距 | 影响 |
|---|------|------|
| 1 | **无双模型机制** — 所有 Agent 使用同一个 LLM | 成本高 (数据搜集也用贵模型) 或质量低 (决策也用便宜模型) |
| 2 | **Agent 输出非 Pydantic** — 当前是 `AgentOpinion` dataclass + free-form raw_data | 跨 Agent 通讯无类型安全, Phase 3 辩论机制难以接入 |
| 3 | **串行执行** — Technical → Intel → Risk → Decision 全程串行 | full 模式下延迟高, 互不依赖的阶段被迫等待 |
| 4 | **无 Agent 级别模型配置** — config 只有一个 `agent_litellm_model` | 无法按角色分配不同成本/能力的模型 |

---

## E1: 双层 LLM 分级调度

### 设计原则

```
deep_think (高质量推理)
  → DecisionAgent, ResearchManager (Phase 3), RiskDebate 裁决
  → 适合: 综合多方信息 + 推理 + 结构化输出

quick_think (快速执行)
  → TechnicalAgent, IntelAgent, RiskAgent, SkillAgent
  → 适合: 数据搜集 + 单视角论述 + 工具调用密集
```

### 实现方案

#### 1. 配置扩展 — `config.py`

```python
# 新增字段
agent_deep_think_model: str = ""   # 深度推理模型 (默认空=继承主模型)
agent_quick_think_model: str = ""  # 快速任务模型 (默认空=继承主模型)
agent_model_assignment: str = "auto"  # "auto" | "single" | "custom"
```

**三种模式**:
- `single`: 所有 Agent 用同一模型（向后兼容，现有行为）
- `auto`: 按角色自动分配 deep/quick（推荐）
- `custom`: 支持 JSON 配置每个 Agent 的模型

#### 2. 模型分配映射

```python
# 默认分配策略 (agent_model_assignment=auto)
MODEL_TIER_MAP = {
    # quick_think tier
    "technical": "quick",
    "intel": "quick",
    "risk": "quick",
    "skill": "quick",
    "bull_researcher": "quick",   # Phase 3
    "bear_researcher": "quick",   # Phase 3
    # deep_think tier
    "decision": "deep",
    "research_manager": "deep",   # Phase 3
    "risk_manager": "deep",       # Phase 3
}
```

#### 3. LLMToolAdapter 扩展

在 `LLMToolAdapter` 中新增 `get_adapter_for_tier(tier: str)` 方法:

```python
class LLMToolAdapter:
    def get_model_for_tier(self, tier: str) -> str:
        """返回指定层级的模型名"""
        if tier == "deep":
            return self._deep_model or self._primary_model
        elif tier == "quick":
            return self._quick_model or self._primary_model
        return self._primary_model

    def call_with_tools_tiered(self, messages, tools, tier="quick", **kwargs):
        """按层级选择模型调用"""
        model = self.get_model_for_tier(tier)
        return self._call_litellm(messages, tools, model=model, **kwargs)
```

#### 4. Orchestrator 集成

在 `_run_stage_agent()` 中注入模型层级:

```python
def _run_stage_agent(self, agent, ctx, ...):
    tier = MODEL_TIER_MAP.get(agent.agent_name, "quick")
    # 将 tier 传入 runner, runner 调用 adapter.call_with_tools_tiered
    ...
```

#### 5. 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `src/config.py` | 新增 `agent_deep_think_model`, `agent_quick_think_model`, `agent_model_assignment` |
| `src/agent/llm_adapter.py` | 新增 `_deep_model`/`_quick_model` 属性, `get_model_for_tier()`, `call_with_tools_tiered()` |
| `src/agent/model_tier.py` | **新建** — `MODEL_TIER_MAP` + `get_tier_for_agent()` 工具函数 |
| `src/agent/runner.py` | `run_agent_loop()` 增加 `model_tier` 参数, 传入 LLM 调用 |
| `src/agent/orchestrator.py` | `_run_stage_agent()` 读取 tier 并传入 runner |

---

## E5: 结构化输出 Schema

### 设计原则

1. **向后兼容**: `AgentOpinion` 保留, 新 Schema 作为 `raw_data` 的类型化替代
2. **渐进升级**: 每个 Agent 逐步迁移到 Pydantic Schema, 不强制一次性替换
3. **失败降级**: LLM 输出无法解析为 Schema 时, fallback 到文本解析 (现有逻辑不变)

### Schema 定义

#### 文件: `src/agent/schemas.py` (新建)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class SignalLevel(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class DataQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ──── 分析师报告 (Technical/Intel/Risk 输出) ────

class AnalystReport(BaseModel):
    """分析师统一输出 — Technical/Intel/Risk Agent 共用"""
    signal: SignalLevel
    confidence: float = Field(ge=0.0, le=1.0)
    key_findings: List[str] = Field(min_length=1, max_length=10)
    risk_factors: List[str] = Field(default_factory=list)
    key_levels: dict = Field(default_factory=dict)
    # e.g. {"support": 1800.0, "resistance": 1950.0}
    data_quality: DataQuality = DataQuality.MEDIUM
    reasoning: str


# ──── 风险裁决 (RiskAgent / RiskManager 输出) ────

class RiskVerdict(BaseModel):
    """风险分析结论"""
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")
    position_limit: str = ""           # "10%" / "30%" / "满仓"
    risk_flags: List[str] = Field(default_factory=list)
    override_signal: bool = False      # 风险一票否决
    reasoning: str


# ──── 最终决策 (DecisionAgent 输出) ────

class FinalDecision(BaseModel):
    """决策 Agent 最终输出"""
    signal: SignalLevel
    confidence: float = Field(ge=0.0, le=1.0)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_suggestion: str = ""      # 轻仓/半仓/重仓
    time_horizon: str = ""             # 短线/波段/中线
    key_reasoning: str = ""
    risk_warnings: List[str] = Field(default_factory=list)

    # 兼容 dashboard 输出格式
    dashboard: Optional[dict] = None


# ──── 研究计划 (Phase 3: ResearchManager 输出) ────

class ResearchPlan(BaseModel):
    """研究主管裁决 (Phase 3 用)"""
    recommendation: str = ""           # Buy/Overweight/Hold/Underweight/Sell
    bull_score: float = Field(ge=0, le=10, default=5.0)
    bear_score: float = Field(ge=0, le=10, default=5.0)
    rationale: str = ""
    strategic_actions: List[str] = Field(default_factory=list)
```

### Agent 输出解析流程

```
LLM raw response text
       │
       ▼
┌──────────────────────────┐
│ 1. 尝试 JSON 提取        │  提取 ```json ... ``` 或裸 JSON
│ 2. Pydantic 验证         │  AnalystReport.model_validate(data)
│ 3. 成功 → 存入 opinion   │  opinion.raw_data["structured"] = report.model_dump()
│    失败 → 文本降级       │  现有 post_process() 逻辑不变
└──────────────────────────┘
```

### 实现步骤

| 步骤 | 文件 | 内容 |
|------|------|------|
| 1 | `src/agent/schemas.py` | **新建** — 所有 Pydantic Schema 定义 |
| 2 | `src/agent/output_parser.py` | **新建** — `parse_structured_output(text, schema_cls)` 通用解析器 |
| 3 | `src/agent/agents/technical_agent.py` | `post_process()` 增加 Schema 解析分支 |
| 4 | `src/agent/agents/intel_agent.py` | 同上 |
| 5 | `src/agent/agents/risk_agent.py` | 输出改为 `RiskVerdict` Schema |
| 6 | `src/agent/agents/decision_agent.py` | 输出改为 `FinalDecision` Schema |
| 7 | `src/agent/protocols.py` | `AgentOpinion` 增加 `structured: Optional[BaseModel]` 字段 |

### Agent Prompt 注入

每个 Agent 的 system prompt 末尾追加输出格式要求:

```python
OUTPUT_FORMAT_INSTRUCTION = """
## Output Format

You MUST return your analysis as a JSON object matching this schema:
{schema_json}

Wrap it in ```json ... ``` code block. Do NOT include any text outside the JSON block.
"""
```

---

## E6: 并行执行优化

### 分析: 哪些阶段可以并行

```
当前 (串行):
  Technical → Intel → Risk → [Skills] → Decision

优化后 (部分并行):
  ┌─ Technical ─┐
  ├─ Intel ─────┤──→ [Skills] ──→ Decision
  └─ Risk ──────┘

理由:
  - Technical / Intel / Risk 互不依赖 (各自用工具搜集数据)
  - Skills 依赖前三者的 opinions (需等待)
  - Decision 依赖所有上游 (必须最后)
```

### 实现方案: 并行阶段分组

#### 新数据结构 — `PipelineStageGroup`

```python
@dataclass
class PipelineStageGroup:
    """一组可并行执行的阶段"""
    agents: List[BaseAgent]
    parallel: bool = True  # True=并行, False=串行

# full 模式的 pipeline 定义
FULL_PIPELINE = [
    PipelineStageGroup(
        agents=[technical, intel, risk],
        parallel=True,  # 并行
    ),
    PipelineStageGroup(
        agents=[*skill_agents],
        parallel=True,  # 多个 skill 之间也并行
    ),
    PipelineStageGroup(
        agents=[decision],
        parallel=False,  # 必须串行
    ),
]
```

#### 执行引擎改造

```python
async def _execute_pipeline_async(self, groups, ctx, ...):
    """按组执行 pipeline, 组内可并行"""
    for group in groups:
        if group.parallel and len(group.agents) > 1:
            # 并行执行
            results = await asyncio.gather(
                *[self._run_stage_agent_async(agent, ctx, ...) for agent in group.agents],
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Stage failed: %s", result)
                else:
                    stats.record_stage(result)
        else:
            # 串行执行
            for agent in group.agents:
                result = await self._run_stage_agent_async(agent, ctx, ...)
                stats.record_stage(result)
```

#### 关键约束: AgentContext 并发安全

`AgentContext` 的 `opinions` 和 `data` 在并行时会被多个 Agent 同时写入，需要保护:

```python
@dataclass
class AgentContext:
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def add_opinion_safe(self, opinion: AgentOpinion):
        async with self._lock:
            self.opinions.append(opinion)

    async def set_data_safe(self, key: str, value: Any):
        async with self._lock:
            self.data[key] = value
```

### 预期收益

| 模式 | 当前耗时 (典型) | 并行后 | 提升 |
|------|---------|--------|------|
| standard (Tech+Intel+Decision) | ~45s | ~30s | -33% |
| full (Tech+Intel+Risk+Decision) | ~65s | ~40s | -38% |
| specialist (Tech+Intel+Risk+Skills×3+Decision) | ~120s | ~60s | -50% |

### 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `src/agent/pipeline.py` | **新建** — `PipelineStageGroup`, `PipelineBuilder`, 各模式的 pipeline 定义 |
| `src/agent/orchestrator.py` | 新增 `_execute_pipeline_async()`, 替换现有 while-loop 状态机 |
| `src/agent/orchestrator.py` | `_run_stage_agent()` → `_run_stage_agent_async()` (async 版本) |
| `src/agent/protocols.py` | `AgentContext` 增加 `_lock` + `add_opinion_safe()` |
| `src/agent/runner.py` | `run_agent_loop()` → `run_agent_loop_async()` (改为 async) |

### 向后兼容策略

- 保留同步 `_execute_pipeline()` 方法, 新增 async 版本
- `run()` 接口不变, 内部用 `asyncio.run()` 或检测已有 event loop
- 新增配置: `agent_parallel_enabled: bool = True` (可回退到串行)

---

## 开发时间线与优先级

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 结构化输出 Schema (E5)                              │
│  优先级: ★★★★★ (Phase 3 辩论机制强依赖)                     │
│  ├─ 1.1 创建 schemas.py + output_parser.py                  │
│  ├─ 1.2 Technical/Intel/Risk 迁移到 AnalystReport           │
│  ├─ 1.3 Decision 迁移到 FinalDecision                       │
│  └─ 1.4 AgentOpinion 增加 structured 字段                   │
├─────────────────────────────────────────────────────────────┤
│  Step 2: 双层 LLM 分级调度 (E1)                              │
│  优先级: ★★★★☆ (降本增效, 立即可见收益)                     │
│  ├─ 2.1 config.py 新增配置字段                               │
│  ├─ 2.2 创建 model_tier.py (分配映射)                        │
│  ├─ 2.3 LLMToolAdapter 扩展 tier 调用                       │
│  └─ 2.4 Orchestrator + Runner 集成                          │
├─────────────────────────────────────────────────────────────┤
│  Step 3: 并行执行优化 (E6)                                   │
│  优先级: ★★★☆☆ (性能优化, 非功能阻塞)                     │
│  ├─ 3.1 创建 pipeline.py (阶段分组定义)                      │
│  ├─ 3.2 AgentContext 并发安全改造                            │
│  ├─ 3.3 Orchestrator 新增 async 执行引擎                    │
│  └─ 3.4 Runner async 化 + 集成测试                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 技术决策与风险

### 做的事

| 决策 | 理由 |
|------|------|
| Pydantic Schema + JSON 文本 fallback | 兼顾类型安全和兼容性, 某些小模型不支持 structured output |
| 逐 Agent 迁移到 Schema | 渐进式升级, 不阻塞其他开发 |
| asyncio.gather 而非 LangGraph | 已有 orchestrator 基础够用, 依赖轻 |
| 双模型可选而非强制 | 用户配置 `agent_model_assignment=single` 可回退 |
| Agent prompt 注入 output schema | 比 LLM function_call/structured_output 兼容性更广 |

### 不做的事

| 排除项 | 理由 |
|--------|------|
| 全部 Agent 强制 async 重写 | 改动过大, 串行降级路径必须保留 |
| 引入 pydantic-ai 或 instructor 库 | 增加依赖, 自行解析 JSON 足够可控 |
| 每个 Agent 独立 LLM 实例 | 过度设计, tier 分两层已覆盖 80% 场景 |
| 重写 runner.py 为全 async | 风险高, 保留同步路径, 新增 async 版本并行共存 |

### 风险与缓解

| 风险 | 缓解 |
|------|------|
| 并行时 AgentContext 竞争条件 | asyncio.Lock 保护写入 |
| LLM 不按 Schema 输出 | output_parser 做 3 层尝试: strict → lenient → fallback |
| quick_think 模型质量不够 | 保留 `agent_model_assignment=single` 回退 |
| async 改造引入 event loop 冲突 | bot/API 已在 async 环境, orchestrator.run() 检测后适配 |
| Schema 变更导致前端兼容性 | FinalDecision.dashboard 字段保留完整 dashboard dict |

---

## 新文件清单

| 文件路径 | 类型 | 职责 |
|---------|------|------|
| `src/agent/schemas.py` | 新建 | Pydantic 结构化输出 Schema (AnalystReport / RiskVerdict / FinalDecision / ResearchPlan) |
| `src/agent/output_parser.py` | 新建 | JSON 提取 + Schema 验证 + fallback 解析器 |
| `src/agent/model_tier.py` | 新建 | MODEL_TIER_MAP + get_tier_for_agent() |
| `src/agent/pipeline.py` | 新建 | PipelineStageGroup + PipelineBuilder + 各模式定义 |
