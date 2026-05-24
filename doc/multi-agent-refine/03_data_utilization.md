# 03 — 数据源最大化利用方案

## 一、问题诊断

### 1.1 DecisionAgent 数据断层

当前 `DecisionAgent.build_user_message()` 仅接收:
- `ctx.opinions` — 各 Agent 的 AgentOpinion
- `ctx.risk_flags` — 风险标记列表

**未接收**:
- `ctx.data["research_plan"]` — Bull/Bear 辩论结论
- `ctx.data["risk_debate_verdict"]` — 三方风险讨论裁决
- `ctx.data["skill_assessments"]` — SkillAgent 详细评估
- 市场全局数据（大盘走势、板块热度）

### 1.2 工具未充分利用

现有工具但未在标准管线中使用:
| 工具 | 现状 | 应该做 |
|------|------|--------|
| `get_market_indices` | 仅 AgentExecutor 可用 | IntelAgent 或新增 MarketContext Agent 使用 |
| `get_sector_rankings` | 仅 AgentExecutor 可用 | IntelAgent 获取板块强弱 |
| `get_portfolio_snapshot` | 仅 AgentExecutor 可用 | 如用户有持仓，Decision 应考虑仓位 |
| `get_skill_backtest_summary` | 仅 SkillAgent 可用 | 应作为 Decision 参考数据 |

### 1.3 数据源能力未完全暴露为工具

`DataFetcherManager` 支持但无对应 Agent 工具:
- 财务报表数据 (fundamental_adapter)
- 分时图数据
- Level2 盘口数据（部分数据源支持）
- 融资融券数据

---

## 二、改造方案

### 2.1 扩展 IntelAgent 工具集

```python
# 当前 IntelAgent 工具
INTEL_TOOLS = [
    "search_stock_news",
    "search_comprehensive_intel",
    "get_stock_info",
    "get_capital_flow",
]

# 新增
INTEL_TOOLS_EXTENDED = [
    ...INTEL_TOOLS,
    "get_market_indices",       # 大盘走势参考
    "get_sector_rankings",      # 板块强弱
    "get_financial_summary",    # 新工具: 财务摘要
]
```

### 2.2 新增工具: get_financial_summary

```python
@tool_registry.register("get_financial_summary")
async def get_financial_summary(symbol: str) -> dict:
    """获取股票关键财务指标摘要(PE/PB/ROE/营收增速/净利增速)"""
    adapter = FundamentalAdapter(fetcher_manager)
    return await adapter.get_summary(symbol)
```

数据源: `fundamental_adapter.py` 已有能力，仅需封装为工具。

### 2.3 DecisionAgent 接入全部上游数据

修改 `DecisionAgent.build_user_message()`:

```python
def build_user_message(self, ctx: AgentContext) -> str:
    sections = []

    # 原有: Agent opinions
    sections.append(self._format_opinions(ctx.opinions))

    # 原有: Risk flags
    if ctx.risk_flags:
        sections.append(self._format_risk_flags(ctx.risk_flags))

    # 🆕 辩论结论
    if research_plan := ctx.get_data("research_plan"):
        sections.append(f"## 多空辩论结论\n{research_plan}")

    # 🆕 风险讨论裁决
    if risk_verdict := ctx.get_data("risk_debate_verdict"):
        sections.append(f"## 风险讨论裁决\n{risk_verdict}")

    # 🆕 技能评估
    if skill_assessments := ctx.get_data("skill_assessments"):
        sections.append(f"## 策略技能评估\n{skill_assessments}")

    # 🆕 市场上下文（如有）
    if market_ctx := ctx.get_data("market_context"):
        sections.append(f"## 当日市场环境\n{market_ctx}")

    return "\n\n---\n\n".join(sections)
```

### 2.4 Dashboard JSON Schema 扩展

新增字段:

```json
{
    "dashboard": {
        // ... 现有字段 ...

        "debate_summary": {
            "bull_core_thesis": "多方核心论点",
            "bear_core_thesis": "空方核心论点",
            "manager_verdict": "裁决结论",
            "confidence_shift": "+10% (辩论后信心变化)"
        },

        "risk_assessment": {
            "aggressive_view": "激进视角简述",
            "conservative_view": "保守视角简述",
            "verdict": "综合风险裁决",
            "max_acceptable_position": "建议最大仓位"
        },

        "market_context": {
            "index_trend": "大盘趋势 (上涨/震荡/下跌)",
            "sector_strength": "所属板块强弱",
            "market_sentiment": "市场情绪 (贪婪/中性/恐惧)"
        },

        "skill_opinions": [
            {
                "skill_name": "策略名",
                "signal": "buy/hold/sell",
                "confidence": 0.0-1.0,
                "key_observation": "核心发现"
            }
        ]
    }
}
```

### 2.5 IntelAgent 增加市场上下文采集

在 IntelAgent 的系统 prompt 中新增指令:

```
除了个股情报外，你还需要:
1. 调用 get_market_indices 获取大盘走势
2. 调用 get_sector_rankings 获取板块排名
3. 将市场环境作为情报的一部分输出
```

IntelAgent 的 opinion 中将包含:
- 个股新闻/情报
- 资金流向
- **市场环境** (大盘走势 + 板块强弱)
- **财务基本面** (PE/PB/ROE 等)

---

## 三、数据流全景图

```
┌──────────────────────────────────────────────────────┐
│                    数据获取层                          │
│  DataFetcherManager (13个数据源)                      │
│  ├─ 实时行情 / 历史K线 / 财务 / 资金流               │
│  ├─ 市场指数 / 板块排名 / 筹码 / 回测                │
│  └─ 新闻搜索 / 综合情报                              │
└───────────────┬──────────────────────────────────────┘
                │ (通过 Agent Tools 暴露)
┌───────────────▼──────────────────────────────────────┐
│                    Agent 管线                          │
│                                                       │
│  TechnicalAgent ──┐                                  │
│    K线+指标+筹码   │  并行                            │
│                    ├──→ RiskAgent ──→ Debate ──→      │
│  IntelAgent ──────┘      风险审查      多空辩论       │
│    新闻+情报+资金                                     │
│    +市场指数+板块                                     │
│    +财务基本面                                        │
│                                                       │
│  → RiskDebate ──→ SkillAgents ──→ DecisionAgent      │
│    三方风险讨论      策略评估          综合决策        │
│                                                       │
│    DecisionAgent 输入:                                │
│    ├─ Technical opinion (技术面)                      │
│    ├─ Intel opinion (情报面+市场环境+基本面)          │
│    ├─ Risk flags (风险标记)                           │
│    ├─ research_plan (辩论结论) 🆕                     │
│    ├─ risk_debate_verdict (风险裁决) 🆕               │
│    ├─ skill_assessments (技能评估) 🆕                 │
│    └─ market_context (大盘+板块) 🆕                   │
└───────────────┬──────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────┐
│              Dashboard JSON 输出                       │
│  ├─ core_conclusion (核心结论)                        │
│  ├─ data_perspective (数据视角: 趋势/价格/量能/筹码) │
│  ├─ intelligence (情报: 新闻/风险/催化剂/情绪)       │
│  ├─ battle_plan (作战计划: 买卖点/仓位/风控)         │
│  ├─ debate_summary (辩论摘要) 🆕                     │
│  ├─ risk_assessment (风险评估) 🆕                    │
│  ├─ market_context (市场环境) 🆕                     │
│  └─ skill_opinions (策略意见) 🆕                     │
└──────────────────────────────────────────────────────┘
```

---

## 四、实现步骤

| # | 任务 | 文件 | 优先级 |
|---|------|------|--------|
| 1 | DecisionAgent 读取 debate/risk 数据 | `agents/decision_agent.py` | P0 |
| 2 | 新增 get_financial_summary 工具 | `tools/data_tools.py` | P1 |
| 3 | IntelAgent 增加市场指数+板块工具 | `agents/intel_agent.py` | P1 |
| 4 | Dashboard Schema 新增字段 | `protocols.py` + Decision prompt | P1 |
| 5 | 前端 DashboardResult 展示新字段 | `DashboardResult.vue` | P1 |
| 6 | Debate 进度事件修复 (type 字段) | `debate.py` | P0 |
| 7 | 市场上下文预注入 (管线启动时) | `orchestrator.py` | P2 |

---

## 五、预期收益

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| DecisionAgent 输入维度 | 2 (opinions + risk_flags) | 6 (+ debate + risk_debate + skills + market) |
| 报告覆盖面 | 技术+部分情报 | 技术+情报+辩论+风险+策略+市场环境 |
| 数据源利用率 | ~50% | ~85% |
| 辩论价值转化 | 0% (结论丢失) | 100% (进入报告) |
