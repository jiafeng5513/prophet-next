# Phase 4 — 交互体验升级 详细实施计划

> 基于已完成的 Phase 1-3（数据基座 + 智能体核心 + 辩论反思），
> Phase 4 聚焦用户交互层：统一 AI 交互入口、K 线信号标注、新闻采集扩展。

---

## 总体目标

从「后端能力强但前端交互单一」升级为「完整的智能交易工作台」：
- **Module D**: 统一 AI 交互入口 — 类 Cursor 的多模式对话界面
- **Module B**: K 线图增强 — Agent 信号标注 + 跨市场适配
- **新闻扩展**: 更多采集源 + 前端消费优化

---

## 现状分析

### 已有基础设施

| 层级 | 已有 | 状态 |
|------|------|------|
| **后端 API** | `/api/v1/agent/chat/stream` (SSE)、`/chat` (同步)、session CRUD | ✅ 完整 |
| **SSE 协议** | event types: thinking/tool_start/tool_done/generating/done/error | ✅ 完整 |
| **WebSocket** | `ws://127.0.0.1:8100/ws/market` 实时行情中继 | ✅ 完整 |
| **K 线图** | KLineChart v9.8.12 (custom fork, prophet-dev 分支) | ✅ 基础可用 |
| **新闻 API** | `/api/v1/news-crawler/*` (采集) + `/api/v1/news/*` (展示) | ✅ 基础可用 |
| **Electron** | 多标签 WebContentsView 架构 | ✅ 可扩展 |
| **前端组件** | News/Report/Chart/Analysis 页面 | ✅ |
| **对话管理** | ConversationManager (后端多轮) | ✅ |
| **缺失** | **Chat UI 组件** / Agent 思考过程可视化 / K 线信号标注层 | ❌ |

### 当前分析流程 (StockAnalysis.vue)

```
用户输入股票代码 → POST /analyze → task_id
         → EventSource /tasks/stream → 进度条 + 状态消息
         → 完成 → 获取报告 → ReportOverview 渲染
```

**问题**: 无对话式交互，无法追问/切换模式/查看 Agent 思考过程。

---

## Module D: 统一 AI 交互入口

### D1: Chat UI 核心组件

#### 设计

```
┌─────────────────────────────────────────────────────┐
│  [模式: Agent集群 ▾]  [标的: 600519 ▾]  [⚙️]       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─ System ─────────────────────────────────────┐   │
│  │ 正在使用 full 模式分析 贵州茅台(600519)...     │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌─ Agent Progress ─────────────────────────────┐   │
│  │ ✅ Technical (2.3s)  ✅ Intel (3.1s)          │   │
│  │ 🔄 Bull∥Bear 辩论 Round 1/2...               │   │
│  │ ⏳ Risk Debate  ⏳ Decision                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌─ Assistant ──────────────────────────────────┐   │
│  │ ## 分析结论                                    │   │
│  │ **信号**: 买入 | **置信度**: 0.78              │   │
│  │ ...                                           │   │
│  │ [查看完整 Dashboard] [在K线标注]               │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [📎] 输入消息...                    [发送] [⏹停止] │
└─────────────────────────────────────────────────────┘
```

#### 新增文件

| 文件 | 用途 |
|------|------|
| `src/renderer/src/Chat.vue` | Chat 页面主视图 |
| `src/renderer/src/components/chat/ChatMessageList.vue` | 消息列表 (虚拟滚动) |
| `src/renderer/src/components/chat/ChatInput.vue` | 输入框 + 模式选择 + 附件 |
| `src/renderer/src/components/chat/ChatMessage.vue` | 单条消息渲染 (支持 Markdown) |
| `src/renderer/src/components/chat/AgentProgress.vue` | Agent 管线进度可视化 |
| `src/renderer/src/components/chat/ThinkingBlock.vue` | 折叠式思考过程展示 |
| `src/renderer/src/components/chat/ToolCallCard.vue` | 工具调用卡片 (name + result) |
| `src/renderer/src/components/chat/StreamRenderer.vue` | SSE 流式文本渲染 |
| `src/renderer/src/service/chatService.ts` | Chat API 封装 + SSE 消费 |
| `src/renderer/src/composables/useChat.ts` | Chat 状态管理 composable |
| `src/renderer/src/composables/useChatStream.ts` | SSE 流式处理 composable |

#### 交互模式

| 模式 | 前端行为 | 后端路由 |
|------|---------|---------|
| **Agent 集群** | 显示 Agent 进度条 + 最终 Dashboard | `/agent/chat/stream` (mode=full/specialist) |
| **快速分析** | 简化进度 + 结论 | `/agent/chat/stream` (mode=quick) |
| **单 Agent** | 指定 agent_id，仅该 Agent 回答 | `/agent/chat/stream` + `agent_id` 参数 |
| **Plan 模式** | 先展示计划 → 用户确认 → 执行 | `/agent/chat/stream` (mode=plan) + 确认交互 |
| **自由对话** | 普通 Chat (无 Agent pipeline) | `/agent/chat/stream` (mode=chat) |

#### SSE 事件 → UI 映射

```typescript
// useChatStream.ts 核心逻辑
interface ChatStreamEvent {
  type: 'thinking' | 'tool_start' | 'tool_done' | 'stage_start' | 'stage_done'
      | 'parallel_start' | 'debate_round' | 'generating' | 'done' | 'error';
  data: Record<string, any>;
}

// 映射到 UI 组件:
// thinking      → ThinkingBlock (折叠)
// tool_start    → ToolCallCard (loading 状态)
// tool_done     → ToolCallCard (完成, 显示摘要)
// stage_start   → AgentProgress (更新当前阶段)
// stage_done    → AgentProgress (标记完成 + 耗时)
// parallel_start→ AgentProgress (并行指示)
// debate_round  → AgentProgress (辩论轮次)
// generating    → StreamRenderer (流式文字)
// done          → ChatMessage (最终消息)
// error         → 错误提示
```

#### 后端新增/修改

| 文件 | 修改 |
|------|------|
| `backend/api/v1/endpoints/agent.py` | 新增 SSE event: `stage_start`/`stage_done`/`debate_round` |
| `backend/src/agent/orchestrator.py` | progress_callback 发送辩论/风险讨论阶段事件 |
| `backend/api/v1/endpoints/agent.py` | 新增 `mode` 参数支持 (plan/chat/single) |
| `backend/api/v1/endpoints/agent.py` | 新增 `agent_id` 参数 (单 Agent 模式) |

### D2: Plan 模式

```
用户: "分析一下贵州茅台"
  ↓ mode=plan
AI: 生成分析计划:
  1. 获取近30日K线 + 技术指标
  2. 搜索近期新闻 + 公告
  3. Bull/Bear 辩论 (2轮)
  4. 风险三方讨论
  5. 综合决策

  [执行计划] [修改] [取消]
  ↓ 用户点击执行
  正常 Agent pipeline 执行...
```

#### 实现方案

```python
# backend: 新增 PlanMode 处理
class PlanModeHandler:
    """Plan 模式: 先生成计划 → 等用户确认 → 再执行"""

    def generate_plan(self, ctx: AgentContext) -> AnalysisPlan:
        """用 quick_think 模型快速生成分析计划"""
        # 输出: 步骤列表 + 预估耗时 + 预估 token

    def execute_plan(self, plan: AnalysisPlan, ctx: AgentContext) -> OrchestratorResult:
        """用户确认后执行"""
```

#### 前端交互

```typescript
// 前端: Plan 确认交互
interface AnalysisPlan {
  steps: Array<{ name: string; description: string; estimated_seconds: number }>;
  total_estimated_seconds: number;
  mode: string;
}

// ChatMessage 中渲染 Plan 卡片:
// - 步骤列表 (可折叠)
// - [执行] [修改] [取消] 按钮
// - 修改: 弹出 modal 让用户调整参数
```

### D3: 会话管理

#### 前端

| 组件 | 用途 |
|------|------|
| `ChatSidebar.vue` | 左侧会话列表 (类 ChatGPT) |
| `SessionItem.vue` | 单个会话条目 (标题 + 时间 + 标的) |

#### 功能

- 新建对话 / 切换对话 / 删除对话
- 自动从第一条消息生成标题
- 按标的/日期筛选
- 导出对话为 Markdown

#### API (已有)

```
GET  /api/v1/agent/chat/sessions         → 会话列表
GET  /api/v1/agent/chat/sessions/{id}    → 历史消息
DELETE /api/v1/agent/chat/sessions/{id}  → 删除
```

### D4: 对话内快捷操作

在消息中渲染可交互操作：

| 操作 | 触发方式 | 效果 |
|------|---------|------|
| 在 K 线标注 | 点击消息中 [在K线标注] 按钮 | 跳转 Chart 标签 + 自动标注买卖点 |
| 追问细节 | 点击 Agent 阶段卡片 | 发送 "详细解释 {agent} 的分析" |
| 切换模式 | 输入 `/mode full` | 切换当前对话的 Agent 模式 |
| 查看原始数据 | 折叠展开 | 展示 Agent 的 raw_data JSON |

---

## Module B: K 线图信号标注

### B1: 标注数据模型

```typescript
// src/renderer/src/types/annotation.ts

interface ChartAnnotation {
  id: string;
  symbol: string;
  timestamp: number;        // Unix ms
  type: 'buy' | 'sell' | 'hold' | 'alert';
  source: 'agent' | 'user' | 'backtest';
  label: string;            // "买入 (0.78)"
  price: number;
  metadata?: {
    agent_mode?: string;    // "full" / "specialist"
    confidence?: number;
    signal?: string;
    session_id?: string;    // 关联的对话 ID
  };
}

interface AnnotationLayer {
  annotations: ChartAnnotation[];
  visible: boolean;
  color: string;
}
```

### B2: 标注渲染 (KLineChart 集成)

```typescript
// src/renderer/src/service/annotationService.ts

class AnnotationService {
  // 从 Agent 分析结果创建标注
  createFromDashboard(dashboard: AgentDashboard): ChartAnnotation;

  // 从回测结果批量创建
  createFromBacktest(results: BacktestResult[]): ChartAnnotation[];

  // 持久化标注 (localStorage + 后端可选)
  save(annotation: ChartAnnotation): void;
  loadForSymbol(symbol: string): ChartAnnotation[];
  remove(id: string): void;
}
```

#### KLineChart 标注 API

```typescript
// 利用 KLineChart 的 createAnnotation API
import { AnnotationType } from 'klinecharts';

// 在 Chart.vue / TVChartContainer.vue 中:
function renderAnnotations(annotations: ChartAnnotation[]) {
  for (const ann of annotations) {
    chart.createAnnotation({
      point: { timestamp: ann.timestamp, value: ann.price },
      styles: {
        symbol: {
          type: ann.type === 'buy' ? 'triangle' : 'diamond',
          color: ann.type === 'buy' ? '#22c55e' : '#ef4444',
        },
        text: { content: ann.label },
      },
    });
  }
}
```

### B3: Agent → Chart 联动

```
分析完成 (Chat页面)
  → 用户点击 [在K线标注]
  → IPC: renderer → main → chart-tab
  → Chart.vue 接收标注数据
  → 渲染买卖点 markers
```

#### IPC 协议

```typescript
// main process: 新增 IPC handler
ipcMain.handle('chart:add-annotations', (event, { symbol, annotations }) => {
  // 找到对应 symbol 的 chart tab (或创建新 tab)
  // 发送 annotations 到 chart tab 的 renderer
  const chartView = findOrCreateChartTab(symbol);
  chartView.webContents.send('chart:annotations-update', annotations);
});
```

### B4: 跨市场时间轴适配

| 市场 | 交易时段 | 非交易时段处理 |
|------|---------|--------------|
| A股 | 09:30-11:30, 13:00-15:00 | 折叠隐藏 |
| 港股 | 09:30-12:00, 13:00-16:00 | 折叠隐藏 |
| 美股 | 09:30-16:00 (ET) | 折叠隐藏 |
| 加密 | 24h | 无折叠 |
| 期货 | 按合约不同 | 动态配置 |

```typescript
// src/renderer/src/service/tradingHours.ts

interface TradingSession {
  start: string;  // "09:30"
  end: string;    // "11:30"
}

const TRADING_HOURS: Record<MarketType, TradingSession[]> = {
  A_SHARE: [{ start: '09:30', end: '11:30' }, { start: '13:00', end: '15:00' }],
  HK: [{ start: '09:30', end: '12:00' }, { start: '13:00', end: '16:00' }],
  US: [{ start: '09:30', end: '16:00' }],
  CRYPTO: [{ start: '00:00', end: '23:59' }],
};

// KLineChart 配置: 非交易时段自动折叠
function configureTradingHours(chart: KLineChart, market: MarketType) {
  // 设置 x 轴时间过滤
}
```

---

## 新闻采集系统扩展

### N1: 新增采集源

| 源 | 类型 | 接入方式 | 优先级 |
|-----|------|---------|-------|
| 雪球 | 社交/评论 | API + 定时抓取 | P0 |
| 财联社 | 快讯 | API / RSS | P0 |
| Reuters | 国际新闻 | RSS | P1 |
| SEC EDGAR | 美股公告 | 官方 API | P1 |
| 巨潮资讯 | A股公告 | 官方 API | P1 |
| StockTwits | 社交 | API | P2 |
| Reddit (WSB) | 社交 | Reddit API | P2 |

#### 新增文件

| 文件 | 用途 |
|------|------|
| `backend/src/services/crawlers/xueqiu_crawler.py` | 雪球快讯 + 热帖 |
| `backend/src/services/crawlers/cls_crawler.py` | 财联社电报 |
| `backend/src/services/crawlers/reuters_crawler.py` | Reuters RSS |
| `backend/src/services/crawlers/sec_crawler.py` | SEC EDGAR filings |
| `backend/src/services/crawlers/cninfo_crawler.py` | 巨潮资讯公告 |

### N2: 前端新闻增强

| 功能 | 实现 |
|------|------|
| 新闻源标签筛选 | NewsFilter.vue 扩展 |
| 实时新闻推送 | WebSocket channel: `news` |
| 新闻 → 对话关联 | 拖拽新闻到 Chat 输入框 |
| 情感趋势图 | 新组件: SentimentChart.vue |
| 新闻热力图 | 按标的聚合，展示新闻密度 |

### N3: 新闻实时推送

```python
# backend: 扩展 realtime_ws.py
# 新增 channel: "news"
# 当 crawler 抓到新新闻时:
#   → broadcast to all subscribed clients
#   → event: {"op": "news", "data": {"id": "...", "title": "...", "source": "..."}}
```

```typescript
// frontend: realtimeWSClient.ts 扩展
subscribeNews(symbols: string[], callback: (news: NewsItem) => void): void;
```

---

## 实施步骤 (按优先级排序)

### Step 1: Chat UI 基础 (D1)

| # | 任务 | 产出 | 预估 |
|---|------|------|------|
| 1.1 | 创建 Chat.vue 页面 + chat.html 入口 | 新标签页 | M |
| 1.2 | ChatMessageList + ChatMessage 组件 | Markdown 渲染 + 虚拟滚动 | M |
| 1.3 | ChatInput 组件 (输入框 + 模式选择) | 模式切换 UI | S |
| 1.4 | useChatStream composable (SSE 消费) | 流式处理核心 | M |
| 1.5 | chatService.ts (API 封装) | HTTP + SSE 封装 | S |
| 1.6 | StreamRenderer 组件 (增量 Markdown) | 打字机效果 | M |
| 1.7 | AgentProgress 组件 (阶段进度) | 管线可视化 | M |
| 1.8 | Electron 注册 Chat 标签类型 | main/index.js | S |

### Step 2: 后端 SSE 增强 (D1 配套)

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | agent.py 新增 stage_start/stage_done/debate_round 事件 | API 增强 |
| 2.2 | orchestrator progress_callback 发送新事件类型 | 辩论/风险阶段事件 |
| 2.3 | 新增 `mode` 请求参数 (quick/standard/full/specialist/plan/chat) | 模式路由 |
| 2.4 | 新增 `agent_id` 参数 (单 Agent 模式) | 单 Agent 路由 |

### Step 3: 会话管理 (D3)

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | ChatSidebar + SessionItem 组件 | 会话列表 UI |
| 3.2 | 会话 CRUD 前端对接 (已有 API) | 前端集成 |
| 3.3 | 自动标题生成 | 首条消息摘要 |
| 3.4 | 会话导出为 Markdown | 工具函数 |

### Step 4: K 线信号标注 (B1-B3)

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | annotation.ts 类型定义 | 数据模型 |
| 4.2 | annotationService.ts (CRUD + 持久化) | 服务层 |
| 4.3 | KLineChart 标注渲染集成 | Chart.vue 修改 |
| 4.4 | IPC: Chat → Main → Chart 标注联动 | main/index.js + Chart.vue |
| 4.5 | 标注管理面板 (显示/隐藏/删除) | Chart.vue 子组件 |

### Step 5: 跨市场时间轴 (B4)

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | tradingHours.ts (时段配置) | 服务层 |
| 5.2 | KLineChart x 轴非交易时段折叠 | Chart 配置 |
| 5.3 | 标的切换时自动适配时区 | Chart.vue 逻辑 |

### Step 6: Plan 模式 (D2)

| # | 任务 | 产出 |
|---|------|------|
| 6.1 | PlanModeHandler 后端实现 | 新增文件 |
| 6.2 | PlanCard 前端组件 (确认/修改/取消) | Chat 子组件 |
| 6.3 | 前端确认 → 触发执行流 | chatService 扩展 |

### Step 7: 新闻采集扩展 (N1-N3)

| # | 任务 | 产出 |
|---|------|------|
| 7.1 | XueqiuCrawler (雪球) | 新 crawler |
| 7.2 | CLSCrawler (财联社) | 新 crawler |
| 7.3 | ReutersCrawler (Reuters RSS) | 新 crawler |
| 7.4 | 新闻实时推送 (WebSocket news channel) | realtime_ws 扩展 |
| 7.5 | 前端 NewsFilter 源筛选 + 实时推送 | 组件增强 |
| 7.6 | 新闻 → Chat 拖拽关联 | 交互增强 |

### Step 8: 对话内快捷操作 (D4)

| # | 任务 | 产出 |
|---|------|------|
| 8.1 | [在K线标注] 按钮 + IPC 触发 | ChatMessage 子组件 |
| 8.2 | `/mode` 斜杠命令解析 | ChatInput 逻辑 |
| 8.3 | Agent 阶段点击追问 | AgentProgress 交互 |

---

## 技术选型

| 需求 | 选型 | 理由 |
|------|------|------|
| Markdown 渲染 | `markdown-it` + `highlight.js` | 已有依赖，轻量 |
| 虚拟滚动 | `vue-virtual-scroller` 或自实现 | 长对话性能 |
| SSE 消费 | 原生 `EventSource` + composable 封装 | 无需额外依赖 |
| 流式文本 | requestAnimationFrame + 增量 DOM | 打字机效果 |
| 标注持久化 | localStorage (前端) + 可选后端 sync | 简单优先 |
| 拖拽 | HTML5 Drag API | 原生即够 |
| 时区处理 | `dayjs` (已有依赖) | 轻量 |

---

## SSE 协议扩展

### 新增事件类型 (后端 → 前端)

```python
# agent.py SSE 新增事件:

# 管线阶段开始
yield f"event: stage_start\ndata: {json.dumps({'stage': 'technical', 'message': 'Starting...'})}\n\n"

# 管线阶段完成
yield f"event: stage_done\ndata: {json.dumps({'stage': 'technical', 'status': 'completed', 'duration': 2.3})}\n\n"

# 并行阶段
yield f"event: parallel_start\ndata: {json.dumps({'agents': ['technical', 'intel']})}\n\n"

# 辩论阶段
yield f"event: debate_round\ndata: {json.dumps({'round': 1, 'total': 2, 'status': 'running'})}\n\n"

# 风险讨论
yield f"event: risk_debate\ndata: {json.dumps({'perspectives': ['aggressive', 'conservative', 'neutral'], 'status': 'running'})}\n\n"

# Plan 模式: 计划已生成，等待确认
yield f"event: plan_ready\ndata: {json.dumps({'plan': {...}})}\n\n"
```

### 前端 SSE 状态机

```typescript
type ChatStreamState =
  | 'idle'
  | 'connecting'
  | 'thinking'        // 收到 thinking 事件
  | 'executing'       // 收到 stage_start / tool_start
  | 'debating'        // 收到 debate_round
  | 'generating'      // 收到 generating (最终文本流)
  | 'done'            // 收到 done
  | 'error';          // 收到 error

// State transitions:
// idle → connecting → thinking → executing → debating → generating → done
//                                                         ↑ error (any state)
```

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| Chat 作为独立标签页 (非侧边栏) | 需要完整宽度展示 Dashboard + 消息 |
| SSE (非 WebSocket) 用于 Agent 流式 | 已有成熟实现，单向推送场景够用 |
| WebSocket 仅用于实时行情 + 新闻推送 | 双向通信场景 |
| Plan 模式用确认交互而非自动执行 | 用户控制感 + 成本可见 |
| 标注存 localStorage 为主 | 简单可靠，后续可加后端 sync |
| 不引入全局状态管理 (Pinia) | 各标签独立，composable 足够 |
| 先做 Chat 核心再做 Plan/单Agent | 核心体验优先 |

---

## 文件树预览 (Phase 4 新增)

```
src/renderer/
├─ chat.html                           # 入口 HTML
├─ src/
│  ├─ chat.ts                          # 入口 JS
│  ├─ Chat.vue                         # Chat 主页面
│  ├─ components/
│  │  └─ chat/
│  │     ├─ ChatMessageList.vue        # 消息列表 (虚拟滚动)
│  │     ├─ ChatMessage.vue            # 单条消息
│  │     ├─ ChatInput.vue              # 输入框 + 控件
│  │     ├─ ChatSidebar.vue            # 会话列表侧栏
│  │     ├─ SessionItem.vue            # 会话条目
│  │     ├─ AgentProgress.vue          # Agent 管线进度
│  │     ├─ ThinkingBlock.vue          # 思考过程折叠
│  │     ├─ ToolCallCard.vue           # 工具调用卡片
│  │     ├─ StreamRenderer.vue         # 流式 Markdown
│  │     └─ PlanCard.vue               # Plan 模式确认卡片
│  ├─ composables/
│  │  ├─ useChat.ts                    # Chat 状态管理
│  │  └─ useChatStream.ts             # SSE 流式处理
│  ├─ service/
│  │  ├─ chatService.ts               # Chat API 封装
│  │  ├─ annotationService.ts         # 标注服务
│  │  └─ tradingHours.ts              # 交易时段配置
│  └─ types/
│     └─ annotation.ts                 # 标注类型定义

backend/
├─ src/
│  ├─ agent/
│  │  └─ plan_mode.py                 # Plan 模式处理器
│  └─ services/
│     └─ crawlers/
│        ├─ xueqiu_crawler.py         # 雪球
│        ├─ cls_crawler.py            # 财联社
│        └─ reuters_crawler.py        # Reuters
```

---

## 成本与性能预估

| 指标 | 当前 (Phase 3) | Phase 4 后 |
|------|----------------|-----------|
| 首次对话响应 | N/A (无 Chat) | <500ms (连接 + thinking 事件) |
| full 模式总延迟 | ~15-30s | 不变 (后端不变) |
| SSE 事件密度 | ~5-8 事件/分析 | ~15-20 事件 (含 stage 细粒度) |
| 前端 bundle 增量 | — | +50KB (markdown-it + 组件) |
| 内存 (长对话) | — | 虚拟滚动控制在 <50MB |

---

## 依赖关系

```
Step 1 (Chat UI 基础) — 无外部依赖，可立即开始
  ↓
Step 2 (SSE 增强) — 依赖 Step 1 的事件消费组件
  ↓
Step 3 (会话管理) — 依赖 Step 1
  ↓ (可并行)
Step 4 (K线标注) — 独立，可与 Step 1-3 并行
Step 5 (跨市场时间) — 独立
Step 6 (Plan 模式) — 依赖 Step 1 + Step 2
Step 7 (新闻扩展) — 独立
Step 8 (快捷操作) — 依赖 Step 1 + Step 4
```

**建议执行顺序**: Step 1 → Step 2 → (Step 3 ∥ Step 4 ∥ Step 5 ∥ Step 7) → Step 6 → Step 8
