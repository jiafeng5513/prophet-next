# 01 — 现有 6 种模式详细分析

## 一、执行入口与路由

```
POST /api/v1/agent/chat/stream
  body: { message, session_id, mode, symbol, skills }
```

路由逻辑:
1. `mode = "plan"` → `PlanModeHandler.generate_plan()` — 不执行管线
2. 其他 mode → `build_agent_executor(config, skills, mode)`:
   - `AGENT_ARCH=multi` → `AgentOrchestrator(mode=mode)`
   - `AGENT_ARCH=single` → `AgentExecutor()` (mode 被忽略)

---

## 二、各模式执行流程

### 1. chat 模式

**定位**: 纯对话，不执行分析工具

**Agent 链** (multi arch): 无管线，直接 LLM 对话
- `response_mode = "chat"` → Decision 输出自然语言而非 Dashboard JSON
- 实际行为: 等同于普通 ChatGPT 式对话

**工具**: 无

**输出**: 自然语言文本

**问题**:
- 与侧边栏 ChatPanel 功能完全重复
- 在 AgentWindow 中出现令人困惑（用户期待分析，却得到闲聊）

---

### 2. quick 模式

**定位**: 快速技术面分析

**Agent 链** (multi arch):
```
TechnicalAgent → DecisionAgent
```

**各 Agent 工具**:
| Agent | 工具 |
|-------|------|
| TechnicalAgent | get_realtime_quote, get_daily_history, analyze_trend, calculate_ma, get_volume_analysis, analyze_pattern, get_chip_distribution, get_analysis_context |
| DecisionAgent | 无（纯合成） |

**数据源利用**: 仅技术面数据（K线、指标、筹码）

**输出**: Dashboard JSON（但缺少情报和风险维度）

**问题**:
- 报告缺少新闻/情报维度，`dashboard.intelligence` 字段为空
- 对于重大利空新闻完全不知情，可能误导用户
- 与 standard 的区别仅在于少了 IntelAgent，用户难以理解何时该用哪个

---

### 3. standard 模式

**定位**: 标准分析（技术+情报）

**Agent 链** (multi arch):
```
[TechnicalAgent ∥ IntelAgent] → DecisionAgent
```
（并行组: Technical 和 Intel 同时执行）

**各 Agent 工具**:
| Agent | 工具 |
|-------|------|
| TechnicalAgent | get_realtime_quote, get_daily_history, analyze_trend, calculate_ma, get_volume_analysis, analyze_pattern, get_chip_distribution, get_analysis_context |
| IntelAgent | search_stock_news, search_comprehensive_intel, get_stock_info, get_capital_flow |
| DecisionAgent | 无 |

**数据源利用**: 技术面 + 新闻情报 + 资金流

**输出**: Dashboard JSON（有 intelligence 字段，但无风险深度分析）

**问题**:
- 无 RiskAgent 审查，高风险场景缺少预警
- 实际上对大多数用户来说是"够用"的默认选择
- 但用户面对 quick/standard/full 三级选择时犹豫不决

---

### 4. full 模式

**定位**: 全面分析（技术+情报+风险+辩论）

**Agent 链** (multi arch):
```
[TechnicalAgent ∥ IntelAgent] → RiskAgent → [Bull/Bear Debate] → [Risk Debate] → DecisionAgent
```

**额外阶段**:
1. **Bull/Bear Debate** (`DebateCoordinator`):
   - 轮次: `AGENT_DEBATE_ROUNDS` (默认 2)
   - BullResearcher + BearResearcher 并行 → 交叉反驳 → ResearchManager 裁决
   - 输出: `ctx.data["research_plan"]`

2. **Risk Debate** (`RiskDebateCoordinator`):
   - AggressiveRiskAnalyst + ConservativeRiskAnalyst + NeutralRiskAnalyst 并行
   - → RiskDebateManager 裁决
   - 输出: `ctx.data["risk_debate_verdict"]`

**各 Agent 工具**:
| Agent | 工具 |
|-------|------|
| TechnicalAgent | (同上) |
| IntelAgent | (同上) |
| RiskAgent | search_stock_news, get_realtime_quote, get_stock_info |
| Debate Agents (×5) | 无工具（纯推理） |
| Risk Analysts (×4) | 无工具（纯推理） |
| DecisionAgent | 无 |

**数据源利用**: 技术面 + 情报 + 风险 + 多角度辩论

**输出**: Dashboard JSON + 辩论过程动画

**问题**:
- ⚠️ **关键缺陷**: DecisionAgent 未读取 `research_plan` 和 `risk_debate_verdict`
- 辩论过程展示了，但结论未进入最终报告，形同虚设
- 延迟较高（6+ LLM 调用），但价值未充分体现
- 与 specialist 的区别仅在于有无 SkillAgent

---

### 5. specialist 模式

**定位**: 专家策略分析（全管线 + 策略技能）

**Agent 链** (multi arch):
```
[TechnicalAgent ∥ IntelAgent] → RiskAgent → [Debate] → [Risk Debate] → [SkillAgent ×1-3] → DecisionAgent
```

**SkillAgent 选择逻辑** (`SkillRouter`):
1. 用户显式传入 `skills` 参数 → 直接使用
2. 自动模式: 检测市场状态 → 匹配 `market_regimes` 标签
3. 兜底: 使用 `default_router=true` 的技能

**SkillAgent 工具**: 由 YAML 策略文件的 `required_tools` 字段定义

**数据源利用**: 技术面 + 情报 + 风险 + 辩论 + 策略评估

**输出**: Dashboard JSON + 辩论 + 技能评估意见

**问题**:
- 需要用户理解"技能"概念并手动选择（或信任自动选择）
- 与 full 相比，仅多了 SkillAgent 阶段
- SkillAgent 的意见通过 `ctx.opinions` 传递给 Decision，权重 20%
- 但用户不知道什么时候该用 specialist 而非 full

---

### 6. plan 模式

**定位**: 先看分析计划，再决定是否执行

**执行流程** (`PlanModeHandler`):
```
用户输入 → LLM 生成结构化分析计划 → 返回前端 → 用户确认 → 以 full/specialist 模式执行
```

**输出**: 分析计划 JSON（步骤列表）

**前端交互**:
- `PlanCard` 组件展示计划
- 用户可: 执行 / 修改 / 取消
- 执行时自动切换到 full 或 specialist 模式

**问题**:
- 本质是"preview before execute"，不是独立模式
- 增加了一次额外交互，多数用户直接跳过
- 应该改为深度分析的可选前置步骤

---

## 三、单 Agent 架构差异

| 特性 | `AGENT_ARCH=multi` | `AGENT_ARCH=single` |
|------|--------------------|--------------------|
| 管线 | 多 Agent 按链执行 | 单一 ReAct 循环 |
| 模式区别 | 不同 Agent 链 | **mode 被忽略** |
| Debate | full/specialist 有 | ❌ 无 |
| Risk Debate | full/specialist 有 | ❌ 无 |
| Skills | specialist 有 | ❌ 无 |
| 工具集 | 按 Agent 分配 | 全量工具可用 |
| 系统 Prompt | 每个 Agent 各有专属 | 统一的 `LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT` |

**结论**: 单 Agent 架构下，无论选什么模式，行为完全一致（ReAct 循环 + 全量工具）。

---

## 四、报告输出元素对比

| Dashboard 字段 | chat | quick | standard | full | specialist |
|---------------|------|-------|----------|------|-----------|
| core_conclusion | ❌(文本) | ✅ | ✅ | ✅ | ✅ |
| data_perspective.trend_status | ❌ | ✅ | ✅ | ✅ | ✅ |
| data_perspective.price_position | ❌ | ✅ | ✅ | ✅ | ✅ |
| data_perspective.volume_analysis | ❌ | ✅ | ✅ | ✅ | ✅ |
| data_perspective.chip_structure | ❌ | ✅ | ✅ | ✅ | ✅ |
| intelligence.latest_news | ❌ | ❌ | ✅ | ✅ | ✅ |
| intelligence.risk_alerts | ❌ | ❌ | ✅ | ✅ | ✅ |
| intelligence.positive_catalysts | ❌ | ❌ | ✅ | ✅ | ✅ |
| battle_plan | ❌ | ✅(简) | ✅ | ✅ | ✅ |
| debate_summary | ❌ | ❌ | ❌ | ⚠️(应有但缺失) | ⚠️(应有但缺失) |
| risk_debate_verdict | ❌ | ❌ | ❌ | ⚠️(应有但缺失) | ⚠️(应有但缺失) |
| skill_opinions | ❌ | ❌ | ❌ | ❌ | ✅ |
| risk_warning | ❌ | ✅(弱) | ✅ | ✅(强) | ✅(强) |

---

## 五、数据源利用矩阵

| 数据源 | chat | quick | standard | full | specialist |
|--------|------|-------|----------|------|-----------|
| 实时行情 (get_realtime_quote) | ❌ | ✅ | ✅ | ✅ | ✅ |
| 历史K线 (get_daily_history) | ❌ | ✅ | ✅ | ✅ | ✅ |
| 技术指标 (analyze_trend) | ❌ | ✅ | ✅ | ✅ | ✅ |
| 筹码分布 (get_chip_distribution) | ❌ | ✅ | ✅ | ✅ | ✅ |
| 新闻搜索 (search_stock_news) | ❌ | ❌ | ✅ | ✅ | ✅ |
| 综合情报 (search_comprehensive_intel) | ❌ | ❌ | ✅ | ✅ | ✅ |
| 资金流 (get_capital_flow) | ❌ | ❌ | ✅ | ✅ | ✅ |
| 股票基本面 (get_stock_info) | ❌ | ❌ | ✅ | ✅ | ✅ |
| 市场指数 (get_market_indices) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 板块排名 (get_sector_rankings) | ❌ | ❌ | ❌ | ❌ | ❌ |
| 回测数据 (backtest_summary) | ❌ | ❌ | ❌ | ❌ | ✅(部分) |
| 历史分析上下文 | ❌ | ✅ | ✅ | ✅ | ✅ |

**关键发现**:
- `get_market_indices` 和 `get_sector_rankings` 在所有分析模式中都未被使用！
- 回测数据仅在 specialist 模式的特定技能中可用
- 大量数据源（基本面详细数据、财务报表等）未被任何 Agent 工具覆盖
