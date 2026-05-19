# Phase 3 — 辩论与反思 详细实施计划 ✅ 已完成 (2026-05-19)

> 基于已完成的 Phase 2 (结构化输出 + 双模型分层 + 并行执行) 继续升级。
> Phase 3 引入多角色对抗辩论和决策记忆反思循环。

---

## 完成状态

| 模块 | 状态 | 产出文件 |
|------|------|---------|
| E2 投资辩论 | ✅ | `agents/bull_researcher.py`, `agents/bear_researcher.py`, `agents/research_manager.py`, `agent/debate.py` |
| E3 风险三方讨论 | ✅ | `agents/risk_debate.py`, `agent/risk_debate_coordinator.py` |
| E4 决策反思 | ✅ | `agent/reflection/models.py`, `agent/reflection/repository.py`, `agent/reflection/service.py` |
| Schema 更新 | ✅ | `schemas.py` += DebateArgument, RiskPerspective |
| model_tier 更新 | ✅ | 7 新 agent → tier 映射 |
| config 更新 | ✅ | 5 新配置项 (debate/risk_debate/reflection) |
| Orchestrator 集成 | ✅ | `_run_debate_phase` / `_run_risk_debate_phase` / `_inject_reflection` / `_record_decision_log` |
| 语法验证 | ✅ | 13/13 文件通过 ast.parse |

### 后续增强 (可选, 不阻塞 Phase 4)

- [ ] E4 定时验证调度 (`reflection/scheduler.py`) — 自动 T+5 价格验证
- [ ] E4 跨标的反思 (`AGENT_REFLECTION_CROSS_TICKER`) — 从其他股票教训中学习
- [ ] E4 API 端点 — 查看决策历史 + 反思记录
- [ ] DecisionAgent 显式注入 `reflection_prompt` 到 user message
- [ ] 辩论进度 WebSocket 推送到前端

---

## 总体目标

将 Agent 编排从「单向流水线」升级为「协作对抗 + 反馈学习」：
- **E2 投资辩论**: 看多/看空对抗，Research Manager 裁决
- **E3 风险三方讨论**: 激进/保守/中立三视角
- **E4 决策记忆与反思**: 持久化决策 → 验证结果 → 生成反思 → 注入 prompt

---

## 架构设计

### 升级后的 full/specialist 模式流水线

```
Phase 2 (已完成):
  [Technical ∥ Intel] → Risk → Decision

Phase 3 (full 模式):
  [Technical ∥ Intel] → [Bull ∥ Bear] → ResearchManager → RiskDebate → Decision
                                                                         ↑
                                                              反思注入 (来自 E4)

Phase 3 (specialist 模式):
  [Technical ∥ Intel] → [Bull ∥ Bear] → ResearchManager → RiskDebate → [Skills] → Decision
```

### 模式兼容策略

| 模式 | 辩论 | 风险三方 | 反思注入 |
|------|------|---------|---------|
| quick | ❌ | ❌ | ✅ (仅注入历史) |
| standard | ❌ | ❌ | ✅ |
| full | ✅ | ✅ | ✅ |
| specialist | ✅ | ✅ | ✅ |

---

## E2: 投资辩论机制

### 设计

```
输入: Technical + Intel 的 AgentOpinion (结构化 AnalystReport)
  ↓
Round 1..N (AGENT_DEBATE_ROUNDS, 默认 2):
  BullResearcher: 基于分析师报告构建看多论据
  BearResearcher: 基于分析师报告构建看空论据 + 反驳 Bull
  ↓
ResearchManager: 综合裁决 → ResearchPlan (已定义在 schemas.py)
  ↓
输出: ResearchPlan 注入 ctx.set_data("research_plan", plan)
     供 RiskDebate + Decision 使用
```

### 新增文件

#### 1. `backend/src/agent/agents/bull_researcher.py`

```python
class BullResearcher(BaseAgent):
    agent_name = "bull_researcher"
    max_steps = 2  # 纯推理，无需 tool call
    tool_names = []

    # 使用 quick_think 模型 (model_tier.py 配置)
    # system_prompt: 你是看多研究员，从分析师报告中找支撑买入的证据
    # build_user_message: 注入 technical + intel 的 AnalystReport
    # post_process: 输出 DebateArgument schema
```

#### 2. `backend/src/agent/agents/bear_researcher.py`

```python
class BearResearcher(BaseAgent):
    agent_name = "bear_researcher"
    max_steps = 2
    tool_names = []

    # 使用 quick_think 模型
    # system_prompt: 你是看空研究员，找风险/利空证据 + 反驳看多论据
    # build_user_message: 注入 technical + intel 报告 + bull 论据 (后续轮)
    # post_process: 输出 DebateArgument schema
```

#### 3. `backend/src/agent/agents/research_manager.py`

```python
class ResearchManager(BaseAgent):
    agent_name = "research_manager"
    max_steps = 2
    tool_names = []

    # 使用 deep_think 模型 (重要裁决)
    # system_prompt: 你是研究主管，综合 Bull/Bear 论据做出裁决
    # build_user_message: 注入所有辩论论据
    # post_process: 输出 ResearchPlan schema (已定义)
```

#### 4. `backend/src/agent/debate.py` (辩论协调器)

```python
class DebateCoordinator:
    """管理多轮 Bull/Bear 辩论 + ResearchManager 裁决"""

    def __init__(self, tool_registry, llm_adapter, config):
        self.rounds = config.agent_debate_rounds  # 默认 2
        self.bull = BullResearcher(tool_registry, llm_adapter)
        self.bear = BearResearcher(tool_registry, llm_adapter)
        self.manager = ResearchManager(tool_registry, llm_adapter)

    def run(self, ctx: AgentContext, timeout_seconds: float) -> List[StageResult]:
        """
        执行辩论流程:
        1. 每轮: Bull 和 Bear 并行执行 (复用 pipeline.py 的 execute_group_parallel)
        2. 每轮结果追加到 ctx.data["debate_history"]
        3. 最后 ResearchManager 裁决
        4. 输出 ResearchPlan → ctx.set_data("research_plan", plan)
        """
```

### 新增 Schema

```python
# 追加到 schemas.py

class DebateArgument(BaseModel):
    """辩论论据 (Bull/Bear Researcher 输出)"""
    stance: str = "bull"  # bull|bear
    key_arguments: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    rebuttals: List[str] = Field(default_factory=list)  # 对对方论据的反驳
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    conclusion: str = ""
```

### model_tier.py 更新

```python
DEFAULT_TIER_MAP 新增:
  "bull_researcher": ModelTier.QUICK,
  "bear_researcher": ModelTier.QUICK,
  "research_manager": ModelTier.DEEP,
```

### 配置项

```python
# config.py 新增
agent_debate_enabled: bool = True        # full/specialist 模式启用
agent_debate_rounds: int = 2             # 辩论轮数 (1-5)

# ENV
AGENT_DEBATE_ENABLED = "true"
AGENT_DEBATE_ROUNDS = "2"
```

### Orchestrator 集成点

在 `_execute_pipeline` 中，Risk 之前插入辩论阶段：

```python
# 在 parallel pre-execution (Technical + Intel) 完成后
# 且在 Risk/Decision 之前:
if self.config.agent_debate_enabled and self.mode in ("full", "specialist"):
    debate_coordinator = DebateCoordinator(...)
    debate_results = debate_coordinator.run(ctx, timeout_seconds=remaining_budget)
    # 记录 stats + tool_calls
    # ResearchPlan 已写入 ctx.data["research_plan"]
```

---

## E3: 风险三方讨论

### 设计

```
输入: 所有前序 opinions + ResearchPlan (来自 E2)
  ↓
三个风险视角并行:
  AggressiveRiskAnalyst:  容忍风险，关注机会成本
  ConservativeRiskAnalyst: 严格风控，关注最大回撤
  NeutralRiskAnalyst:      概率加权，均衡评估
  ↓
RiskManager: 汇总三方意见 → RiskVerdict (已定义在 schemas.py)
  ↓
替代原有的单一 RiskAgent (保留 RiskAgent 作为 standard 模式的简化版)
```

### 新增文件

#### 1. `backend/src/agent/agents/risk_debate.py`

```python
class AggressiveRiskAnalyst(BaseAgent):
    agent_name = "risk_aggressive"
    max_steps = 3
    tool_names = ["search_stock_news", "get_realtime_quote"]
    # quick_think; 关注机会成本、仓位限制过严的代价

class ConservativeRiskAnalyst(BaseAgent):
    agent_name = "risk_conservative"
    max_steps = 3
    tool_names = ["search_stock_news", "get_realtime_quote", "get_stock_info"]
    # quick_think; 关注最大回撤、黑天鹅、VaR

class NeutralRiskAnalyst(BaseAgent):
    agent_name = "risk_neutral"
    max_steps = 3
    tool_names = ["search_stock_news", "get_realtime_quote"]
    # quick_think; 概率加权、历史胜率分析

class RiskManager(BaseAgent):
    agent_name = "risk_manager"
    max_steps = 2
    tool_names = []
    # deep_think; 综合三方意见，输出 RiskVerdict
```

#### 2. `backend/src/agent/risk_debate.py` (风险讨论协调器)

```python
class RiskDebateCoordinator:
    """管理三方风险讨论 + RiskManager 裁决"""

    def __init__(self, tool_registry, llm_adapter, config):
        self.rounds = config.agent_risk_debate_rounds  # 默认 1
        self.analysts = [
            AggressiveRiskAnalyst(tool_registry, llm_adapter),
            ConservativeRiskAnalyst(tool_registry, llm_adapter),
            NeutralRiskAnalyst(tool_registry, llm_adapter),
        ]
        self.manager = RiskManager(tool_registry, llm_adapter)

    def run(self, ctx: AgentContext, timeout_seconds: float) -> List[StageResult]:
        """
        1. 三方并行执行 (execute_group_parallel)
        2. RiskManager 裁决 → RiskVerdict
        3. 写入 ctx risk_flags + set_data("risk_verdict", verdict)
        """
```

### 新增 Schema

```python
# 追加到 schemas.py

class RiskPerspective(BaseModel):
    """单一风险视角分析 (Aggressive/Conservative/Neutral)"""
    perspective: str = "neutral"  # aggressive|conservative|neutral
    risk_assessment: str = ""     # 综合评估
    position_recommendation: str = ""  # 建议仓位
    key_concerns: List[str] = Field(default_factory=list)
    opportunities_missed: List[str] = Field(default_factory=list)  # 仅 aggressive 填写
    worst_case_scenario: str = ""  # 仅 conservative 填写
    probability_weighted_outcome: str = ""  # 仅 neutral 填写
    overall_risk_score: float = Field(default=50.0, ge=0.0, le=100.0)
```

### model_tier.py 更新

```python
DEFAULT_TIER_MAP 新增:
  "risk_aggressive": ModelTier.QUICK,
  "risk_conservative": ModelTier.QUICK,
  "risk_neutral": ModelTier.QUICK,
  "risk_manager": ModelTier.DEEP,
```

### 配置项

```python
# config.py 新增
agent_risk_debate_enabled: bool = True   # full/specialist 模式启用
agent_risk_debate_rounds: int = 1        # 讨论轮数 (通常 1 轮足够)

# ENV
AGENT_RISK_DEBATE_ENABLED = "true"
AGENT_RISK_DEBATE_ROUNDS = "1"
```

### Orchestrator 集成

full/specialist 模式下，用 `RiskDebateCoordinator` **替代**原有的单一 `RiskAgent`：

```python
if self.config.agent_risk_debate_enabled and self.mode in ("full", "specialist"):
    # 使用三方风险讨论替代 RiskAgent
    risk_debate = RiskDebateCoordinator(...)
    risk_results = risk_debate.run(ctx, timeout_seconds=remaining_budget)
else:
    # standard/quick 模式保持原有 RiskAgent
    result = self._run_stage_agent(risk_agent, ctx, ...)
```

---

## E4: 决策记忆与反思循环

### 设计

```
阶段 1: 决策记录 (分析完成时)
  DecisionAgent 输出 → 持久化 DecisionLogEntry (signal/price/reasoning)

阶段 2: 结果验证 (下次分析同标的时)
  查询 5 天/20 天后的实际价格 → 计算收益率 + alpha

阶段 3: 反思生成 (验证后)
  LLM 分析: 做对了什么 / 错在哪里 / 环境特征

阶段 4: 反思注入 (分析开始前)
  将高质量反思片段注入 Agent prompt 上下文
```

### 新增文件

#### 1. `backend/src/agent/reflection/models.py` (数据模型)

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from src.storage import Base

class DecisionLog(Base):
    """决策记录表"""
    __tablename__ = "decision_log"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True)
    market = Column(String(10))
    analysis_date = Column(DateTime, index=True)
    signal = Column(String(20))          # strong_buy/buy/hold/sell/strong_sell
    confidence = Column(Float)
    key_reasoning = Column(Text)
    price_at_decision = Column(Float)
    sentiment_score = Column(Float)      # 来自 dashboard

    # 结果验证 (后续填充)
    price_5d = Column(Float, nullable=True)
    price_20d = Column(Float, nullable=True)
    return_5d = Column(Float, nullable=True)   # 5日收益率 %
    return_20d = Column(Float, nullable=True)  # 20日收益率 %
    alpha_5d = Column(Float, nullable=True)    # vs benchmark
    alpha_20d = Column(Float, nullable=True)
    outcome_verified = Column(Boolean, default=False)
    verified_date = Column(DateTime, nullable=True)

    # 反思 (LLM 生成)
    reflection = Column(Text, nullable=True)
    reflection_quality = Column(Float, nullable=True)  # 0-1 (自评)
    lesson_tags = Column(String(200), nullable=True)   # comma-separated

    created_at = Column(DateTime)
    updated_at = Column(DateTime, nullable=True)
```

#### 2. `backend/src/agent/reflection/repository.py` (数据访问)

```python
class DecisionLogRepository:
    """决策日志 CRUD + 查询"""

    def save_decision(self, entry: DecisionLog) -> int: ...
    def get_pending_verification(self, days_threshold=5) -> List[DecisionLog]: ...
    def get_history_for_symbol(self, symbol: str, limit=5) -> List[DecisionLog]: ...
    def get_recent_lessons(self, limit=3) -> List[DecisionLog]: ...
    def update_outcome(self, id: int, price_5d, price_20d, benchmark_5d, benchmark_20d): ...
    def update_reflection(self, id: int, reflection: str, quality: float, tags: List[str]): ...
```

#### 3. `backend/src/agent/reflection/service.py` (核心服务)

```python
class ReflectionService:
    """决策反思服务"""

    def __init__(self, repo: DecisionLogRepository, llm_adapter: LLMToolAdapter, config):
        self.repo = repo
        self.llm = llm_adapter
        self.config = config

    def record_decision(self, ctx: AgentContext, dashboard: dict) -> None:
        """分析完成后记录决策"""
        # 从 ctx 提取 signal/confidence/price → 写入 DecisionLog

    def verify_pending_outcomes(self) -> int:
        """
        定时任务: 查找 >=5 天前的未验证决策 → 拉取当前价格 → 计算收益
        返回: 验证数量
        """

    def generate_reflection(self, entry: DecisionLog) -> str:
        """
        LLM 生成反思:
        输入: 当时信号/推理 + 实际结果 + 市场环境
        输出: 2-3 句教训总结
        用 quick_think 模型
        """

    def get_reflection_context(self, symbol: str) -> str:
        """
        获取注入 prompt 的反思上下文:
        1. 同标的最近 N 条反思 (AGENT_REFLECTION_LOOKBACK)
        2. 跨标的最近 N 条高质量教训 (AGENT_REFLECTION_CROSS_TICKER)
        3. 格式化为 Markdown 片段
        """
```

#### 4. `backend/src/agent/reflection/scheduler.py` (定时验证)

```python
class ReflectionScheduler:
    """定时执行结果验证 + 反思生成"""

    async def run_verification_cycle(self):
        """
        每日执行:
        1. 查找待验证决策 (>=5天)
        2. 拉取当前/历史价格
        3. 计算收益率 + alpha
        4. 生成反思
        """
```

### 集成到 Agent Pipeline

#### 反思注入 (分析开始前)

在 `base_agent.py` 或 `orchestrator.py` 中：

```python
# orchestrator._execute_pipeline() 开头:
if self.config.agent_reflection_enabled:
    reflection_ctx = reflection_service.get_reflection_context(ctx.stock_code)
    if reflection_ctx:
        ctx.set_data("reflection_context", reflection_ctx)

# 在 DecisionAgent.build_user_message() 中:
reflection = ctx.get_data("reflection_context")
if reflection:
    parts.append("## Historical Reflection")
    parts.append(reflection)
```

#### 决策记录 (分析完成后)

```python
# orchestrator._execute_pipeline() 末尾:
if self.config.agent_reflection_enabled and dashboard:
    reflection_service.record_decision(ctx, dashboard)
```

### 配置项

```python
# config.py 新增
agent_reflection_enabled: bool = False    # 默认关闭，需显式开启
agent_reflection_lookback: int = 5        # 同标的最近 N 条反思
agent_reflection_cross_ticker: int = 3    # 跨标的最近 N 条教训
agent_reflection_verify_days: int = 5     # N 天后验证结果
agent_benchmark_map: str = ""             # JSON: {"A_SHARE": "000300.SH", ...}

# ENV
AGENT_REFLECTION_ENABLED = "false"
AGENT_REFLECTION_LOOKBACK = "5"
AGENT_REFLECTION_CROSS_TICKER = "3"
AGENT_REFLECTION_VERIFY_DAYS = "5"
AGENT_BENCHMARK_MAP = '{"A_SHARE":"000300.SH","HK":"HSI","US":"SPY","CRYPTO":"BTC-USDT"}'
```

---

## 实施步骤 (按优先级排序)

### Step 1: E2 投资辩论 (核心对抗机制)

| # | 任务 | 产出文件 |
|---|------|---------|
| 1.1 | 新增 DebateArgument Schema | `schemas.py` 追加 |
| 1.2 | 创建 BullResearcher Agent | `agents/bull_researcher.py` |
| 1.3 | 创建 BearResearcher Agent | `agents/bear_researcher.py` |
| 1.4 | 创建 ResearchManager Agent | `agents/research_manager.py` |
| 1.5 | 创建 DebateCoordinator | `agent/debate.py` |
| 1.6 | model_tier.py 添加新 agent 映射 | `model_tier.py` 修改 |
| 1.7 | config.py 添加辩论配置 | `config.py` 修改 |
| 1.8 | Orchestrator 集成辩论阶段 | `orchestrator.py` 修改 |
| 1.9 | 辩论阶段并行执行 (Bull∥Bear) | 复用 `pipeline.py` |

### Step 2: E3 风险三方讨论

| # | 任务 | 产出文件 |
|---|------|---------|
| 2.1 | 新增 RiskPerspective Schema | `schemas.py` 追加 |
| 2.2 | 创建三视角 Risk Analysts | `agents/risk_debate.py` |
| 2.3 | 创建 RiskManager Agent | 同上文件 |
| 2.4 | 创建 RiskDebateCoordinator | `agent/risk_debate_coordinator.py` |
| 2.5 | model_tier.py 添加映射 | `model_tier.py` 修改 |
| 2.6 | config.py 添加风险讨论配置 | `config.py` 修改 |
| 2.7 | Orchestrator 替换 RiskAgent (full模式) | `orchestrator.py` 修改 |

### Step 3: E4 决策记忆与反思

| # | 任务 | 产出文件 |
|---|------|---------|
| 3.1 | 创建 DecisionLog SQLAlchemy model | `agent/reflection/models.py` |
| 3.2 | 创建 Repository | `agent/reflection/repository.py` |
| 3.3 | 创建 ReflectionService | `agent/reflection/service.py` |
| 3.4 | config.py 添加反思配置 | `config.py` 修改 |
| 3.5 | Orchestrator 集成: 反思注入 + 决策记录 | `orchestrator.py` 修改 |
| 3.6 | DecisionAgent 注入反思上下文 | `agents/decision_agent.py` 修改 |
| 3.7 | 创建定时验证调度 | `agent/reflection/scheduler.py` |
| 3.8 | API 端点: 查看决策历史 + 反思 | `api/v1/` 新增 |

---

## LLM 调用成本估算 (full 模式单次分析)

| 阶段 | Agent 数 | 模型 | 预估 token |
|------|---------|------|-----------|
| Technical + Intel (并行) | 2 | quick | ~4000 |
| Bull + Bear × 2轮 (并行) | 4 次调用 | quick | ~6000 |
| ResearchManager | 1 | deep | ~2000 |
| Risk × 3 (并行) + RiskManager | 4 | quick×3 + deep×1 | ~6000 |
| Decision | 1 | deep | ~3000 |
| **合计** | **~12 次调用** | — | **~21000 token** |

对比 Phase 2 full 模式: ~4 次调用, ~8000 token → 成本约 2.5x，延迟因并行不变太多。

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| Bull/Bear 用 quick_think | 单视角论述不需要深度推理，控制成本 |
| 辩论轮数可配 (默认 2) | 多轮提升质量但增加成本/延迟，用户可调 |
| 风险讨论仅 1 轮 | 三视角已提供足够多样性，多轮收益递减 |
| 反思默认关闭 | 需要持续运行验证任务，初始阶段可选 |
| 辩论/风险讨论仅 full/specialist | quick/standard 追求速度，不增加复杂度 |
| ResearchPlan 写入 ctx.data | 不新增 AgentOpinion，避免污染 opinions 列表 |
| 反思用 SQLite | 与现有 storage.py 一致，无需新依赖 |
| 结果验证 T+5 天 | 平衡短期噪声和反馈延迟 |
