# 多 Agent 增强计划 — 借鉴 TradingAgents 框架

> 基于 [TauricResearch/TradingAgents](https://github.com/tauricresearch/tradingagents)（73.5k star，LangGraph 多 Agent 金融交易框架）的核心设计理念，结合 prophet-next 现有架构进行增强。

## 一、现状分析

### prophet-next 现有 Agent 架构

```
AgentOrchestrator (orchestrator.py)
├─ TechnicalAgent    — 技术分析 (K线/MA/趋势/量价/筹码)
├─ IntelAgent        — 情报搜集 (新闻/公告/资金流)
├─ RiskAgent         — 风险筛查 (减持/业绩预警/监管)
├─ SkillAgent        — 策略技能 (YAML策略匹配)
├─ DecisionAgent     — 综合决策 (汇总→Dashboard JSON)
└─ PortfolioAgent    — 组合分析 (仓位/相关性/风控)

执行模式:
  quick    : Technical → Decision
  standard : Technical → Intel → Decision
  full     : Technical → Intel → Risk → Decision
  specialist: Technical → Intel → Risk → Skill → Decision
```

**优势**: 多模式灵活、YAML 策略热加载、LiteLLM 多模型适配、超时降级  
**不足**: 单向流水线 → 每阶段仅单一视角，无辩论/对抗机制；无决策反思闭环

### TradingAgents 核心亮点

| 特性 | 说明 |
|------|------|
| 多角色对抗辩论 | Bull/Bear Researcher 辩论 → Research Manager 裁决；Aggressive/Conservative/Neutral 三方风险讨论 |
| 决策记忆 + 反思 | 每次决策持久化 → 下次获取真实收益率 → LLM 反思 → 注入后续分析 |
| DAG 并行工作流 | LangGraph 有向图，4 分析师并行 → 辩论 → 决策 |
| 双层 LLM 分级 | deep_think (复杂推理) vs quick_think (快速任务) |
| 结构化输出 Schema | Pydantic 模型确保输出可靠解析 |
| Checkpoint 断点续跑 | 崩溃后从上一成功节点恢复 |

---

## 二、开发计划

### Phase 1: 双层 LLM 分级调度（1-2天）

**目标**: 按任务复杂度使用不同规格 LLM，降本提速。

**现状**: `llm_adapter.py` 通过 LiteLLM 支持多模型，但 orchestrator 所有 Agent 共用同一 adapter 实例。

**改动范围**:
- `backend/src/config.py` — 新增 `AGENT_DEEP_THINK_MODEL` 和 `AGENT_QUICK_THINK_MODEL` 配置项
- `backend/src/agent/factory.py` — 构建两个 LLMToolAdapter 实例
- `backend/src/agent/orchestrator.py` — 按 Agent 角色分配不同 adapter
- `backend/src/agent/agents/base_agent.py` — 支持接收指定的 adapter

**分配策略**:
```
deep_think → DecisionAgent, RiskAgent, SkillAgent (需要深度推理)
quick_think → TechnicalAgent, IntelAgent (数据搜集整理为主)
```

**实现要点**:
```python
# config.py 新增
AGENT_DEEP_THINK_MODEL = "agent_deep_think_model"    # e.g. "gpt-4o"
AGENT_QUICK_THINK_MODEL = "agent_quick_think_model"  # e.g. "gpt-4o-mini"

# orchestrator.py 修改
self.deep_adapter = build_adapter(config.deep_think_model)
self.quick_adapter = build_adapter(config.quick_think_model)
# Technical/Intel 用 quick，Risk/Decision 用 deep
```

**验证**: 对比同一个股分析的耗时和 token 消耗变化。

---

### Phase 2: 决策记忆与反思循环（3-5天）

**目标**: 建立"分析→验证→反思→改进"的闭环学习机制。

**现状**: `memory.py` 已有 `AgentMemory` 框架 (`CalibrationResult`, `AnalysisMemoryEntry`)，但反思循环尚未实现。

**改动范围**:
- `backend/src/agent/memory.py` — 扩展，新增 `DecisionLog` 类
- `backend/src/agent/reflection.py` — **新建**，决策反思生成器
- `backend/src/agent/agents/decision_agent.py` — 注入历史决策 + 反思到 prompt
- `backend/src/agent/orchestrator.py` — 在 pipeline 起始处触发待定反思解析
- 数据库 migration — `analysis_decisions` 表

**数据模型**:
```python
@dataclass
class DecisionLogEntry:
    stock_code: str
    analysis_date: str
    signal: str              # buy/hold/sell
    confidence: float
    key_reasoning: str       # 决策关键理由摘要
    price_at_decision: float
    # 以下字段在后续反思时填充
    outcome_5d: Optional[float] = None   # 5日收益率
    outcome_20d: Optional[float] = None  # 20日收益率
    alpha_vs_benchmark: Optional[float] = None
    reflection: Optional[str] = None     # LLM 生成的反思
    resolved_at: Optional[str] = None
```

**反思流程**:
```
1. 分析完成 → 写入 DecisionLogEntry (signal + reasoning + price)
2. 下次分析同一 stock_code 时:
   a. 查找 pending entries (无 outcome)
   b. 获取实际收益率 (yfinance / 数据源)
   c. 计算 alpha (vs 沪深300/恒生/SPY)
   d. LLM 生成一段反思 (做对了什么 / 错在哪里)
   e. 更新 entry
3. 注入 DecisionAgent prompt:
   "以下是你对该股票的历史分析记录和反思: ..."
```

**验证**: 检查反思内容是否合理影响后续同一股票的分析结论。

---

### Phase 3: 投资辩论机制（5-7天）

**目标**: 在 `full` 和 `specialist` 模式下，引入 Bull/Bear 对抗辩论，增强分析多角度覆盖。

**改动范围**:
- `backend/src/agent/agents/bull_researcher.py` — **新建**
- `backend/src/agent/agents/bear_researcher.py` — **新建**
- `backend/src/agent/agents/research_manager.py` — **新建**
- `backend/src/agent/protocols.py` — 新增 `DebateState` 数据结构
- `backend/src/agent/orchestrator.py` — 新增辩论阶段 (在 Intel 之后、Decision 之前)

**辩论数据结构**:
```python
@dataclass
class DebateState:
    bull_arguments: List[str] = field(default_factory=list)
    bear_arguments: List[str] = field(default_factory=list)
    round_count: int = 0
    max_rounds: int = 2  # 可配置
    judge_summary: str = ""
```

**辩论流程**:
```
Technical + Intel 完成后:
  ┌──────────────────────────────────────────┐
  │  Round 1:                                │
  │    BullResearcher → 看多论据             │
  │    BearResearcher → 看空论据 (反驳)       │
  │  Round 2:                                │
  │    BullResearcher → 补充 (回应反驳)       │
  │    BearResearcher → 补充 (进一步质疑)      │
  │  ResearchManager → 综合裁决              │
  └──────────────────────────────────────────┘
  裁决结果注入 DecisionAgent context
```

**Pipeline 变更**:
```
full 模式 (改前): Technical → Intel → Risk → Decision
full 模式 (改后): Technical → Intel → Debate → Risk → Decision

specialist 模式 (改前): Technical → Intel → Risk → Skill → Decision
specialist 模式 (改后): Technical → Intel → Debate → Risk → Skill → Decision
```

**配置项**:
```python
# config.py
AGENT_DEBATE_ENABLED = "agent_debate_enabled"        # bool, 默认 False
AGENT_DEBATE_ROUNDS = "agent_debate_rounds"          # int, 默认 2
```

**BullResearcher prompt 核心**:
```
你是看多研究员。基于技术和情报分析结果，构建看多论点:
1. 识别正面催化剂和增长驱动力
2. 回应看空方的反驳
3. 评估上行空间和概率
```

**BearResearcher prompt 核心**:
```
你是看空研究员。基于相同分析结果，构建看空论点:
1. 识别风险因素和估值问题
2. 反驳看多方的论据
3. 评估下行风险和概率
```

**验证**: 对比有/无辩论模式的分析深度和方向准确率。

---

### Phase 4: 风险三方讨论（3-5天）

**目标**: 升级 RiskAgent 为三方讨论机制，覆盖激进/保守/中性风控视角。

**改动范围**:
- `backend/src/agent/agents/risk_agent.py` — 重构为三角色
- `backend/src/agent/agents/risk_debaters.py` — **新建** (Aggressive / Conservative / Neutral)
- `backend/src/agent/protocols.py` — 新增 `RiskDebateState`

**三方角色**:
```
AggressiveRiskAnalyst  — 偏向容忍风险，关注机会成本
ConservativeRiskAnalyst — 严格风控，关注最大回撤和黑天鹅
NeutralRiskAnalyst      — 平衡两方，给出概率加权评估
```

**讨论流程**:
```
Aggressive → Conservative → Neutral (1轮)
→ 可配置多轮 → RiskAgent 汇总裁决
```

---

### Phase 5: 结构化输出 Schema（2-3天）

**目标**: 用 Pydantic 模型约束各 Agent 的输出格式，替代 JSON 自由文本解析。

**现状**: 各 Agent 的 `post_process()` 用 `try_parse_json` 从 raw text 提取 JSON，容易出错。

**改动范围**:
- `backend/src/agent/schemas.py` — **新建**，定义所有 Agent 的输出 Schema
- `backend/src/agent/agents/*.py` — 各 Agent 使用 structured output
- `backend/src/agent/runner.py` — 支持 schema 验证

**Schema 定义**:
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

class TechnicalOpinion(BaseModel):
    signal: SignalLevel
    confidence: float = Field(ge=0, le=1)
    trend: str                    # "上升" / "下降" / "震荡"
    support_levels: List[float]
    resistance_levels: List[float]
    key_indicators: dict
    reasoning: str

class RiskAssessment(BaseModel):
    risk_level: str               # "low" / "medium" / "high" / "critical"
    risk_flags: List[dict]
    override_signal: bool = False # 是否风险一票否决
    reasoning: str

class DebateSummary(BaseModel):
    bull_score: float = Field(ge=0, le=10)
    bear_score: float = Field(ge=0, le=10)
    consensus: SignalLevel
    key_bull_points: List[str]
    key_bear_points: List[str]
    judge_reasoning: str

class FinalDecision(BaseModel):
    signal: SignalLevel
    confidence: float = Field(ge=0, le=1)
    target_price: Optional[float]
    stop_loss: Optional[float]
    position_suggestion: str      # "轻仓" / "半仓" / "重仓"
    time_horizon: str             # "短线" / "波段" / "中线"
    key_reasoning: str
    risk_warnings: List[str]
```

---

### Phase 6: 并行分析优化（3-5天）

**目标**: 在 `full`/`specialist` 模式中，将互不依赖的 Agent 并行执行。

**现状**: `orchestrator.py` 严格顺序执行 `for stage_name, agent in self._build_stage_list()`。

**改动范围**:
- `backend/src/agent/orchestrator.py` — 引入 `asyncio.gather` 或 `concurrent.futures` 并行阶段

**并行拓扑**:
```
            ┌─ TechnicalAgent ─┐
  开始 ──→ │                    │──→ Debate ──→ Risk ──→ Decision
            └─ IntelAgent ──────┘
```

Technical 和 Intel 无依赖关系，可以并行。Debate 依赖两者结果，后续顺序执行。

**实现要点**:
```python
async def _run_parallel_stage(self, agents, ctx):
    tasks = [agent.run(ctx) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**预估收益**: `full` 模式总耗时减少 30-40%（Technical 和 Intel 各约 10-15s，并行后取 max）。

---

## 三、实施路线图

```
Week 1:  Phase 1 (双层LLM) + Phase 5 (结构化输出)
         ── 低风险改动，立即见效

Week 2:  Phase 2 (决策记忆 + 反思)
         ── 核心闭环，需要数据库 migration

Week 3:  Phase 3 (投资辩论)
         ── 最大价值特性，需要新增 3 个 Agent

Week 4:  Phase 4 (风险三方讨论) + Phase 6 (并行优化)
         ── 可选增强 + 性能优化
```

## 四、配置项汇总

```python
# === Phase 1: 双层 LLM ===
AGENT_DEEP_THINK_MODEL = "gpt-4o"          # 复杂推理用
AGENT_QUICK_THINK_MODEL = "gpt-4o-mini"    # 快速任务用

# === Phase 2: 决策记忆 ===
AGENT_REFLECTION_ENABLED = True            # 启用反思循环
AGENT_REFLECTION_LOOKBACK = 5             # 注入最近 N 条同 ticker 反思
AGENT_REFLECTION_CROSS_TICKER = 3          # 注入最近 N 条跨 ticker 教训
AGENT_BENCHMARK_MAP = {                    # alpha 基准
    "A-share": "000300.SH",   # 沪深300
    "HK": "HSI",              # 恒生指数
    "US": "SPY",              # 标普500
}

# === Phase 3: 投资辩论 ===
AGENT_DEBATE_ENABLED = False               # full/specialist 模式启用
AGENT_DEBATE_ROUNDS = 2                    # 辩论轮数

# === Phase 4: 风险讨论 ===
AGENT_RISK_DEBATE_ENABLED = False          # 三方风险讨论
AGENT_RISK_DEBATE_ROUNDS = 1              # 讨论轮数
```

## 五、不做的事项

以下 TradingAgents 的设计**不适合** prophet-next 照搬:

1. **LangGraph 整体替换** — prophet-next 的 orchestrator 已足够灵活，无需引入 LangGraph 依赖。
   通过 `asyncio` 即可实现并行。
2. **Markdown 文件持久化** — TradingAgents 用 `.md` 文件存决策日志，prophet-next 应继续用
   SQLAlchemy/数据库，更利于查询和 UI 展示。
3. **Checkpoint 断点续跑** — prophet-next 单次分析耗时可控（<2min），无需引入 checkpoint 复杂度。
4. **yfinance 数据源依赖** — prophet-next 已有完善的 data_provider 多源架构
   (akshare/baostock/tushare/binance/okx 等)，保持现有设计。

## 六、风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| 辩论增加 LLM 调用次数 (成本+延迟) | 辩论默认关闭，仅 full/specialist 可选启用；使用 quick_think 模型 |
| 反思注入过多历史 context | 限制注入条数 (5条)，截断过长的反思文本 |
| 结构化输出 schema 不匹配 | 保留 fallback：schema 解析失败时回退到 raw text 解析 |
| 并行执行的异常处理 | gather 中 return_exceptions=True，单个失败不阻塞其他 |
| 数据库 migration 兼容 | 新表 `analysis_decisions`，不修改现有表结构 |
