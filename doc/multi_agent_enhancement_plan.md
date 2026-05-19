# Prophet-Next 智能交易终端 — 全面升级开发计划

> 基于 [TauricResearch/TradingAgents](https://github.com/tauricresearch/tradingagents) 的多智能体协作理念，结合 prophet-next 现有 Electron + FastAPI + Vue 3 架构，实现一个面向全球多市场（A股/港股/美股/加密货币/大宗商品期货）的智能交易终端。

---

## 一、愿景与核心需求

| # | 需求 | 说明 |
|---|------|------|
| 1 | **统一行情数据层** | A股/港股/美股/加密货币/大宗商品期货 — 来源多样但统一缓存格式，供后端全局使用 |
| 2 | **专业 K 线图** | 人工看盘级的 K 线显示，支持指标叠加、多周期切换 |
| 3 | **桌面客户端承载** | Electron 桌面应用，非 CLI 工具 |
| 4 | **新闻资讯采集系统** | 社交网络 + 财经新闻持续采集→清洗→持久化，形成可回测数据集 |
| 5 | **统一 AI 交互入口** | 类 Cursor/Copilot 的交互范式：Agent 集群模式 / 单 Agent 模式 / Plan 模式 / 闲聊模式 |
| 6 | **智能体编排升级** | 借鉴 TradingAgents 的多角色对抗辩论、结构化通讯、决策反思闭环 |

---

## 二、现状分析

### 2.1 prophet-next 现有架构

```
Electron 主进程
├─ WebContentsView (多标签: Chart / News / Portfolio / Analysis / Settings)
├─ FastAPI 子进程 (backend/)
│   ├─ AgentOrchestrator (multi-agent pipeline)
│   │   ├─ TechnicalAgent    — 技术分析
│   │   ├─ IntelAgent        — 情报搜集
│   │   ├─ RiskAgent         — 风险筛查
│   │   ├─ SkillAgent        — 策略技能 (YAML)
│   │   ├─ DecisionAgent     — 综合决策
│   │   └─ PortfolioAgent    — 组合分析
│   ├─ DataFetcherManager (多数据源: akshare/baostock/tushare/binance/okx/yfinance/longbridge)
│   ├─ ConversationManager (多轮对话)
│   └─ SQLite 持久化 (market_cache.db)
└─ Vue 3 前端 (src/renderer/)
```

**已有优势**:
- 多模式 Agent 流水线（quick/standard/full/specialist）
- 多数据源 + 熔断器 + 故障转移
- LiteLLM 多模型适配
- Electron 多标签桌面应用
- K 线图 + 新闻流页面已有基础

**不足**:
- Agent 编排为单向流水线，无辩论/对抗
- 无决策反思闭环
- 数据采集偏 A 股，全球市场覆盖不完整
- 新闻仅展示，未形成持久化数据集
- AI 交互入口单一（仅分析模式），缺少统一交互范式

### 2.2 TradingAgents 可借鉴之处

| 特性 | TradingAgents 实现 | prophet-next 适配策略 |
|------|-------------------|---------------------|
| Bull/Bear 对抗辩论 | 多轮 debate → Research Manager 裁决 | 借鉴辩论结构，集成到 full/specialist 模式 |
| 三方风险讨论 | Aggressive/Conservative/Neutral | 升级 RiskAgent 为三视角讨论 |
| 决策记忆 + 反思 | markdown 日志 + yfinance 验证 | 用 SQLite 持久化 + 多数据源验证 |
| 结构化输出 Schema | Pydantic (ResearchPlan/TraderDecision) | 统一各 Agent 输出为 Pydantic Schema |
| DAG 并行 | LangGraph StateGraph | 用 asyncio.gather 实现，无需引入 LangGraph |
| 双层 LLM | deep_think / quick_think | 按角色分配模型 |

---

## 三、模块划分与开发计划

### Module A: 统一行情数据层（数据基座）

**目标**: 无论数据源是 akshare、tushare、binance、okx、longbridge 还是 yfinance，所有市场的行情数据都规范化为统一 OHLCV 格式，本地缓存后供图表、分析、回测全链路使用。

**现状**: `DataFetcherManager` 已有多源架构 + 故障转移 + `market_cache.db`，但各市场覆盖不均。

**关键工作**:

1. **统一 OHLCV 数据模型**
   ```python
   @dataclass
   class UnifiedBar:
       symbol: str          # 统一编码: "600519.SH" / "AAPL" / "BTC-USDT" / "GC=F"
       market: MarketType   # A_SHARE / HK / US / CRYPTO / FUTURES
       timestamp: datetime
       open: Decimal
       high: Decimal
       low: Decimal
       close: Decimal
       volume: Decimal
       turnover: Optional[Decimal] = None  # 成交额
       period: str = "1d"   # 1m/5m/15m/1h/4h/1d/1w/1M
   ```

2. **数据源 → 市场映射表**
   | 市场 | 主数据源 | 备用数据源 | 实时行情 |
   |------|---------|-----------|---------|
   | A股 | akshare/tushare | baostock/efinance | pytdx |
   | 港股 | longbridge | yfinance | longbridge WS |
   | 美股 | yfinance | longbridge | — |
   | 加密货币 | binance | okx | binance/okx WS |
   | 大宗商品期货 | yfinance | — | — |

3. **缓存策略**
   - SQLite WAL 模式，按 `(symbol, period)` 分表或分区
   - 请求时先查本地缓存，缺失区间才远程拉取并回填
   - 设置页可视化管理缓存范围（时间轴 UI，已有设计）

4. **增量更新与数据质量**
   - 每次拉取自动检测并补全缺失 bar
   - 异常值检测：涨跌幅 > 阈值时标记 flag
   - 复权因子管理（A股/港股需要前复权/后复权）

---

### Module B: K 线图与人工看盘

**目标**: 提供专业级 K 线图看盘体验，支持多指标叠加和多周期切换。

**现状**: `Chart.vue` 已集成 K 线图库（KlineChart），基础功能可用。

**关键工作**:

1. **数据对接**: K 线图从 Module A 的统一缓存层读取数据
2. **多周期**: 1m / 5m / 15m / 1h / 4h / 日 / 周 / 月
3. **指标系统**: MA / EMA / BOLL / MACD / RSI / KDJ / Vegas 通道等
4. **标注层**: 支持在 K 线上叠加 Agent 分析信号点（买入/卖出标记）
5. **跨市场**: 切换标的时自动适配交易时间段（A股 9:30-15:00 / 美股 9:30-16:00 / 加密 24h）

---

### Module C: 新闻资讯采集与数据集化

**目标**: 持续采集财经新闻/社交媒体信息，清洗后持久化为可回测的结构化数据集。

**现状**: `News.vue` 有新闻展示页面，后端有搜索能力，但未形成持续采集 + 持久化管线。

**关键工作**:

1. **采集源定义**
   | 来源类型 | 具体渠道 | 采集方式 |
   |---------|---------|---------|
   | 财经新闻 | 东方财富/新浪财经/同花顺/Reuters/Bloomberg | RSS / API / 爬虫 |
   | 社交媒体 | 雪球/StockTwits/Reddit(WSB)/Twitter | API / 定时抓取 |
   | 公告 | 巨潮资讯/港交所/SEC EDGAR | 官方 API |
   | 宏观数据 | 央行公报/统计局/Fed | 定时拉取 |

2. **统一新闻数据模型**
   ```python
   @dataclass
   class NewsItem:
       id: str                      # UUID
       source: str                  # "eastmoney" / "xueqiu" / "reuters"
       source_url: str
       title: str
       content: str                 # 全文或摘要
       publish_time: datetime
       crawl_time: datetime
       symbols: List[str]           # 关联标的 ["600519.SH", "AAPL"]
       tags: List[str]              # 标签 ["earnings", "macro", "insider"]
       sentiment_score: Optional[float]  # -1.0 ~ 1.0 (LLM 打分)
       language: str                # "zh" / "en"
       market: MarketType
   ```

3. **采集调度器**
   - 后台定时任务（可配置频率: 5min/15min/1h）
   - 增量采集：每个源维护 `last_crawl_cursor`
   - 去重：基于 `(source, source_url)` 唯一约束
   - 异常重试 + 告警

4. **数据集化**
   - SQLite / DuckDB 持久化，支持按 symbol/date/source 查询
   - 导出能力：CSV / Parquet 格式，可导入 backtest 框架
   - 定期统计：数据量、覆盖率、缺失报告
   - 与 Module A 行情数据通过 `(symbol, date)` 关联 → 形成完整的可回测时序数据

5. **LLM 增强处理**
   - 自动摘要生成（长文 → 一句话）
   - 情感打分（-1 ~ +1）
   - 关联标的识别（从新闻文本提取股票代码）
   - 重要性分级（high/medium/low）

---

### Module D: 统一 AI 交互入口

**目标**: 提供类 Cursor/Copilot 的统一 AI 交互界面，用户可选择不同模式与系统交互。

**现状**: `ConversationManager` 已支持多轮对话，分析流通过 API 触发，但缺少统一交互范式。

**关键工作**:

1. **交互模式定义**

   | 模式 | 说明 | 对标 |
   |------|------|------|
   | **Agent 集群** | 全自动多 Agent 协作分析 (full/specialist pipeline) | Cursor Agent 模式 |
   | **单 Agent** | 指定单一专家对话（如仅技术分析、仅风控） | Cursor 选择具体 Agent |
   | **Plan 模式** | AI 先生成分析计划 → 用户确认 → 再执行 | Copilot Plan 模式 |
   | **闲聊模式** | 自由对话，不触发分析流水线 | 普通 Chat |
   | **回测模式** | 基于历史数据集运行策略验证 | — |

2. **前端 UI 设计**
   ```
   ┌────────────────────────────────────────────┐
   │  [模式选择器 ▾]  [模型选择 ▾]  [标的 ▾]    │
   ├────────────────────────────────────────────┤
   │                                            │
   │  对话历史区域                                │
   │  - 用户消息                                 │
   │  - Agent 响应 (含思考过程折叠)               │
   │  - 阶段进度指示器                            │
   │                                            │
   ├────────────────────────────────────────────┤
   │  [输入框]                    [发送] [附件]   │
   └────────────────────────────────────────────┘
   ```

3. **模式路由器** (后端)
   ```python
   class InteractionRouter:
       def route(self, message: str, mode: str, context: dict) -> AgentPipeline:
           match mode:
               case "cluster":    return self.orchestrator.run_full(...)
               case "single":     return self.run_single_agent(context["agent_id"], ...)
               case "plan":       return self.generate_plan_then_confirm(...)
               case "chat":       return self.free_chat(...)
               case "backtest":   return self.run_backtest(...)
   ```

4. **流式输出**
   - SSE / WebSocket 实时推送 Agent 思考过程
   - 每个 Agent 阶段完成时推送中间结果
   - 支持取消正在进行的分析

5. **上下文管理**
   - 当前标的自动注入对话上下文
   - K 线图选中区域可作为分析输入
   - 新闻条目可拖入对话作为参考素材

---

### Module E: 智能体编排升级（核心 — 借鉴 TradingAgents）

**目标**: 从单向流水线升级为多角色对抗协作的 DAG 工作流。

#### E1: 双层 LLM 分级调度

按任务复杂度分配不同规格 LLM：

```
deep_think (gpt-4o / claude-sonnet-4-20250514 / deepseek-r1)
  → DecisionAgent, ResearchManager, RiskDebate 裁决
  → 需要深度推理的关键节点

quick_think (gpt-4o-mini / claude-haiku / deepseek-v3)
  → TechnicalAgent, IntelAgent, Bull/Bear Researcher
  → 数据搜集整理、单视角论述
```

#### E2: 投资辩论机制

```
分析师团并行完成后:
  ┌─────────────────────────────────────────────────────┐
  │  Round 1~N (可配置):                                 │
  │    BullResearcher → 看多论据 (基于分析师报告)          │
  │    BearResearcher → 看空论据 + 反驳                   │
  │  ResearchManager → 综合裁决 (结构化输出: ResearchPlan) │
  └─────────────────────────────────────────────────────┘
  ResearchPlan 注入后续 Trader / Risk / Decision
```

**新增 Agent**:
- `bull_researcher.py` — 看多研究员
- `bear_researcher.py` — 看空研究员
- `research_manager.py` — 研究主管 (裁决者)

#### E3: 风险三方讨论

升级 RiskAgent 为三视角讨论机制：

```
AggressiveRiskAnalyst  → 容忍风险，关注机会成本
ConservativeRiskAnalyst → 严格风控，关注最大回撤
NeutralRiskAnalyst      → 概率加权评估

讨论 N 轮 → RiskManager 汇总裁决
```

#### E4: 决策记忆与反思循环

```
分析完成 → 记录 DecisionLogEntry (signal/price/reasoning)
         ↓
下次分析同一标的 → 获取实际收益率 → 计算 alpha
         ↓
LLM 生成反思 (做对了什么 / 错在哪里)
         ↓
注入后续分析的 prompt 上下文
```

**数据模型**:
```python
class DecisionLogEntry(BaseModel):
    symbol: str
    market: MarketType
    analysis_date: date
    signal: SignalLevel            # strong_buy / buy / hold / sell / strong_sell
    confidence: float
    key_reasoning: str
    price_at_decision: Decimal
    # 反思阶段填充
    outcome_5d: Optional[float] = None
    outcome_20d: Optional[float] = None
    alpha_vs_benchmark: Optional[float] = None
    reflection: Optional[str] = None
```

#### E5: 结构化输出 Schema

统一各 Agent 的输出为 Pydantic 模型，确保跨 Agent 通讯可靠解析：

```python
class AnalystReport(BaseModel):
    """分析师统一输出格式"""
    signal: SignalLevel
    confidence: float = Field(ge=0, le=1)
    key_findings: List[str]
    data_quality: str              # "high" / "medium" / "low"
    reasoning: str

class ResearchPlan(BaseModel):
    """研究主管裁决输出"""
    recommendation: PortfolioRating  # Buy/Overweight/Hold/Underweight/Sell
    bull_score: float = Field(ge=0, le=10)
    bear_score: float = Field(ge=0, le=10)
    rationale: str
    strategic_actions: List[str]

class RiskVerdict(BaseModel):
    """风险裁决输出"""
    risk_level: str                # low/medium/high/critical
    position_limit: str            # 建议仓位上限
    risk_flags: List[str]
    override_signal: bool = False  # 风险一票否决
    reasoning: str

class FinalDecision(BaseModel):
    """最终决策输出"""
    signal: SignalLevel
    confidence: float = Field(ge=0, le=1)
    target_price: Optional[float]
    stop_loss: Optional[float]
    position_suggestion: str       # 轻仓/半仓/重仓
    time_horizon: str              # 短线/波段/中线
    key_reasoning: str
    risk_warnings: List[str]
```

#### E6: DAG 并行执行

```
            ┌─ TechnicalAgent ─┐
 开始 ──→  ├─ IntelAgent ──────┤──→ Debate ──→ Risk Debate ──→ Decision
            └─ NewsAgent ───────┘
```

用 `asyncio.gather` 实现互不依赖节点的并行，无需引入 LangGraph：

```python
# 并行阶段
parallel_results = await asyncio.gather(
    technical_agent.run(ctx),
    intel_agent.run(ctx),
    news_agent.run(ctx),
    return_exceptions=True,
)
# 汇总后进入辩论阶段
```

---

### Module F: 全局标的管理与跨市场支持

**目标**: 统一标的编码体系，支持跨市场的标的浏览、搜索、收藏。

**关键工作**:

1. **统一标的编码**
   ```
   A股:    600519.SH / 000858.SZ
   港股:    00700.HK
   美股:    AAPL / NVDA
   加密:    BTC-USDT / ETH-USDT
   期货:    GC=F / CL=F / AU2506.SHF
   ```

2. **标的元数据**
   ```python
   class SymbolInfo(BaseModel):
       symbol: str
       name: str                  # "贵州茅台" / "Apple Inc."
       market: MarketType
       exchange: str              # "SSE" / "SZSE" / "HKEX" / "NASDAQ" / "Binance"
       sector: Optional[str]
       currency: str              # "CNY" / "HKD" / "USD" / "USDT"
       trading_hours: str         # 交易时段描述
       lot_size: int = 1         # 最小交易单位
   ```

3. **收藏列表 + 分组**: 用户自定义 watchlist，跨市场混合

---

## 四、升级后的完整工作流

```
用户在统一交互入口选择:

[Agent 集群模式] + 标的 "600519.SH"
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ 1. 数据准备 (并行)                                    │
│    ├─ 行情缓存层 → OHLCV + 指标计算                   │
│    ├─ 新闻数据集 → 最近 N 天相关新闻                    │
│    └─ 基本面数据 → 财报/公告                           │
│                                                       │
│ 2. 分析师团并行                                        │
│    ├─ TechnicalAgent → 技术面报告 (AnalystReport)     │
│    ├─ IntelAgent → 情报报告 (AnalystReport)           │
│    └─ NewsAgent → 新闻舆情报告 (AnalystReport)         │
│                                                       │
│ 3. 投资辩论                                           │
│    ├─ BullResearcher × N 轮                           │
│    ├─ BearResearcher × N 轮                           │
│    └─ ResearchManager → ResearchPlan                  │
│                                                       │
│ 4. 风险讨论                                           │
│    ├─ Aggressive / Conservative / Neutral             │
│    └─ RiskManager → RiskVerdict                       │
│                                                       │
│ 5. 最终决策                                           │
│    └─ DecisionAgent → FinalDecision                  │
│       (注入: 历史反思 + ResearchPlan + RiskVerdict)    │
│                                                       │
│ 6. 决策持久化 + 前端展示                                │
│    ├─ 写入 DecisionLog (待后续反思)                    │
│    ├─ 推送 Dashboard 到前端                           │
│    └─ 在 K 线图上标注信号点                            │
└─────────────────────────────────────────────────────┘
```

---

## 五、实施路线图

```
Phase 1 — 数据基座夯实 ✅ (2026-05-19 完成)
  ├─ ✅ Module A: 统一行情数据层
  │     ├─ MarketGateway 单例 (多市场 K线/实时行情/标的列表)
  │     ├─ DataSourceChain 优先级路由 (TickFlow→各市场备用源)
  │     ├─ KlineCacheManager (SQLite WAL, 增量补全, 间隙分析)
  │     ├─ MarketType / PeriodType 枚举 (backend/src/enums.py)
  │     └─ WebSocket 实时行情中继 (realtime_ws.py, 自动降级轮询)
  ├─ ✅ Module C: 新闻采集管线 MVP
  │     ├─ CrawledNewsItem 统一数据模型
  │     ├─ BaseCrawler 抽象基类 (含股票代码正则提取)
  │     ├─ EastMoneyCrawler (东方财富全球快讯 API, A/全球/港/美栏目)
  │     ├─ NewsRepository (SQLite 持久化, 去重, 按标的/时间查询)
  │     ├─ NewsCrawlScheduler (5min 定时采集, 回调机制)
  │     ├─ NewsProcessor (LLM 摘要+情感分析+重要性分级)
  │     └─ API: /api/v1/news-crawler/* (status/start/stop/run-once/feed/process)
  └─ ✅ Module F: 统一标的编码 + 元数据管理
        ├─ tickflow_symbol.py (跨市场编码转换 600519↔600519.SH)
        └─ WatchlistService (自选列表 CRUD, 跨市场混合)

Phase 2 — 智能体核心升级
  ├─ E1: 双层 LLM 分级调度
  ├─ E5: 结构化输出 Schema
  └─ E6: 并行执行优化

Phase 3 — 辩论与反思
  ├─ E2: 投资辩论机制 (Bull/Bear + ResearchManager)
  ├─ E3: 风险三方讨论
  └─ E4: 决策记忆与反思循环

Phase 4 — 交互体验
  ├─ Module D: 统一 AI 交互入口
  ├─ Module B: K 线图增强（信号标注 + 跨市场适配）
  └─ 新闻采集系统完善 (更多源: 雪球/财联社/Reuters)
```

---

## 六、技术决策与原则

### 做的事

| 决策 | 理由 |
|------|------|
| 用 asyncio 实现并行，不引入 LangGraph | orchestrator 已足够灵活，LangGraph 引入过重 |
| SQLite/DuckDB 持久化，不用 Markdown 文件 | 更利于查询、统计、UI 展示 |
| 用 Pydantic 结构化输出 + fallback | 保证解析可靠性，失败时降级为文本解析 |
| 保持现有 data_provider 多源架构 | 已有 akshare/baostock/tushare/binance/okx/longbridge 等 |
| 自建新闻数据集，不依赖开源数据集 | 开源数据集覆盖有限且不可控，自建可定制化 |
| Electron + FastAPI 子进程架构不变 | 已验证可行，前后端分离清晰 |

### 不做的事

| 排除项 | 理由 |
|--------|------|
| LangGraph 整体替换 | 过重，asyncio 足够 |
| Checkpoint 断点续跑 | 单次分析 <2min，不值得引入复杂度 |
| 照搬 yfinance / Alpha Vantage 依赖 | 已有更丰富的数据源 |
| 实盘交易执行 | 当前阶段专注分析和回测，不做自动下单 |
| 移动端 | 桌面端优先，后续再考虑 |

---

## 七、配置项汇总

```python
# === 双层 LLM ===
AGENT_DEEP_THINK_MODEL = "deepseek-r1"         # 复杂推理
AGENT_QUICK_THINK_MODEL = "deepseek-v3"        # 快速任务

# === 投资辩论 ===
AGENT_DEBATE_ENABLED = True                    # full/specialist 模式启用
AGENT_DEBATE_ROUNDS = 2                        # 辩论轮数

# === 风险讨论 ===
AGENT_RISK_DEBATE_ENABLED = True               # 三方风险讨论
AGENT_RISK_DEBATE_ROUNDS = 1                   # 讨论轮数

# === 决策反思 ===
AGENT_REFLECTION_ENABLED = True                # 反思循环
AGENT_REFLECTION_LOOKBACK = 5                  # 同标的最近 N 条
AGENT_REFLECTION_CROSS_TICKER = 3              # 跨标的最近 N 条教训
AGENT_BENCHMARK_MAP = {
    "A_SHARE": "000300.SH",   # 沪深300
    "HK": "HSI",              # 恒生指数
    "US": "SPY",              # S&P 500
    "CRYPTO": "BTC-USDT",     # BTC 作为基准
    "FUTURES": None,          # 期货无统一基准
}

# === 新闻采集 ===
NEWS_CRAWL_INTERVAL_MINUTES = 15               # 采集频率
NEWS_SOURCES_ENABLED = ["eastmoney", "xueqiu", "reuters"]
NEWS_SENTIMENT_MODEL = "quick_think"           # 情感打分用快模型
NEWS_MAX_AGE_DAYS = 365                        # 最长保留

# === 交互模式 ===
DEFAULT_INTERACTION_MODE = "cluster"           # cluster/single/plan/chat/backtest
STREAM_OUTPUT_ENABLED = True                   # 流式输出
```

---

## 八、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 辩论增加 LLM 调用次数 (成本 + 延迟) | Bull/Bear 用 quick_think；辩论轮数可配置；闲时预缓存 |
| 新闻采集触发反爬/限流 | 控制频率 + 多 IP + 优先用官方 API |
| 全球市场时区复杂 | 内部统一用 UTC，展示层按市场时区转换 |
| 数据源 API 变更/停服 | 多源故障转移 + 定期监控 + 社区更新 |
| 反思注入过多 context | 限制条数 + 截断 + 只注入高质量反思 |
| 结构化输出不兼容某些模型 | 保留 JSON 文本解析 fallback |
| 新闻数据量膨胀 | 定期归档 + 分表 + 压缩存储 |
