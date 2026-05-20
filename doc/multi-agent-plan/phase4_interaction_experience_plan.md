# Phase 4 — 交互体验升级 详细实施计划

> 基于已完成的 Phase 1-3（数据基座 + 智能体核心 + 辩论反思），
> Phase 4 聚焦用户交互层：统一 AI 交互入口、K 线信号标注、新闻采集扩展。

---

## 总体目标

从「后端能力强但前端交互单一」升级为「完整的智能交易工作台」：
- **Module D**: 双层 AI 交互入口 — 侧边栏轻量对话 + 独立 Agent 窗口深度分析（参考 VS Code Copilot 模式）
- **Module B**: K 线图增强 — Agent 信号标注 + 跨市场适配
- **新闻扩展**: 更多采集源 + 前端消费优化

---

## 设计理念

### 参考 VS Code Copilot 的双层交互范式

VS Code 中有两种 AI 交互方式，各有分工：
- **Copilot Chat (侧边栏)**: 轻量问答，快速代码补全建议，不占用编辑器空间
- **Copilot Agent (独立面板)**: 自主多步操作，调用工具，修改多文件，需要进度可视化

Prophet-Next 采用相同理念：
- **侧边栏 Chat Panel**: 快速问答、闲聊、单 Agent 轻量分析
- **Agent Window (独立窗口)**: 完整 Agent 集群分析、多角色辩论、Plan 模式

### 核心设计决策

| 决策 | 说明 |
|------|------|
| **辩论模式仅限 Agent Window** | Bull/Bear 对抗辩论 + Risk 三方讨论过程复杂、耗时长、需要进度可视化，侧边栏空间无法承载 |
| **合并旧入口** | 原有的 `initAgentChat` (问股) + 侧边栏聊天 → 统一为新的 Vue 组件化侧边栏 Chat Panel |
| **左上角 Agent 启动按钮** | 参考 VS Code 左上角布局，在侧边栏开关按钮旁新增 Agent 窗口启动按钮，提供全局快速入口 |
| **共享会话** | 侧边栏和 Agent Window 共享 session_id，分析结果可在侧边栏追问 |

### 模式分配策略

| 模式 | 侧边栏 Chat | Agent Window | 说明 |
|------|:-----------:|:------------:|------|
| **chat** (自由对话) | ✅ | ❌ | 纯 LLM 问答，无 pipeline |
| **quick** (快速分析) | ✅ | ❌ | tech → decision，秒级响应 |
| **单 Agent** | ✅ | ❌ | 指定 agent_id 直接回答 |
| **standard** (标准分析) | ✅ | ✅ | tech → intel → decision，侧边栏的增强模式 / Agent Window 的轻量模式 |
| **full** (完整分析) | ❌ | ✅ | 含 Bull/Bear 辩论 + Risk 讨论 |
| **specialist** (专家分析) | ❌ | ✅ | full + 策略专家 agents |
| **plan** (计划模式) | ❌ | ✅ | 先生成计划 → 用户确认 → 执行 |

**用户体验路径**: 侧边栏快问快答 → 不满意 → 一键升级到 Agent Window 深度分析

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
| **辩论机制** | Bull/Bear Debate + Risk Debate (Phase 3) | ✅ 仅 full/specialist 模式 |
| **缺失** | **Chat UI 组件** / Agent 思考过程可视化 / K 线信号标注层 | ❌ |

### 当前分析流程 (StockAnalysis.vue)

```
用户输入股票代码 → POST /analyze → task_id
         → EventSource /tasks/stream → 进度条 + 状态消息
         → 完成 → 获取报告 → ReportOverview 渲染
```

**问题**: 无对话式交互，无法追问/切换模式/查看 Agent 思考过程。

### 当前问股 (侧边栏 initAgentChat)

```
侧边栏输入问题 → POST /agent/chat/stream (SSE)
         → 流式显示回答 (thinking/generating/done)
         → 支持多轮对话 + 技能选择
```

**问题**: 实现为原生 DOM (index.js)，无组件化；无 Agent 管线进度可视化；与市场分析割裂。

### 合并策略

| 现有入口 | 归宿 | 说明 |
|---------|------|------|
| 侧边栏问股 (initAgentChat) | → **侧边栏 Chat Panel** | Vue 组件化重构，保持侧边栏位置，增强功能 |
| 市场分析 (StockAnalysis.vue) | → **Agent Window** | 独立窗口承接完整分析管线，StockAnalysis 废弃 |

---

## Module D: 双层 AI 交互入口

> 参考 VS Code Copilot Chat (侧边栏) + Agent 模式 (独立面板) 的设计。

### 架构概览

```
+--------------------------------------------------------------+
|  Electron Main Window                                         |
|  +--------+---------------------------------------------+    |
|  |[≡][🤖]|  Tabs: [Chart] [News] [Report] ...           |    |
|  |        |                                              |    |
|  |Sidebar |                                              |    |
|  |+------+|                                              |    |
|  || Chat ||          (主内容区)                            |    |
|  || Panel||                                              |    |
|  ||      ||                                              |    |
|  || 轻量 ||                                              |    |
|  || 对话 ||                                              |    |
|  ||      ||                                              |    |
|  |+------+|                                              |    |
|  +--------+---------------------------------------------+    |
+--------------------------------------------------------------+

  [≡] = 侧边栏开关按钮 (已有)
  [🤖] = Agent 窗口启动按钮 (新增，左上角紧邻侧边栏按钮)

        用户点击 [🤖] 或快捷键 Ctrl+Shift+A
                          |
                          v

+--------------------------------------------------------------+
|  Agent Window (独立窗口)                                       |
|  +----------------------------------------------------------+ |
|  | [模式: ▾ full] [标的: 600519] [设置]          [x 关闭]    | |
|  +----------------------------------------------------------+ |
|  |  Agent Progress:                                          | |
|  |  ✅ Technical  ✅ Intel  🔄 Debate (Round 1/2)  ○ Risk   | |
|  |                                                           | |
|  |  ┌─ 🐂 Bull Researcher ──────────────────────┐           | |
|  |  │ "基于近3月技术面突破..."                      │           | |
|  |  └──────────────────────────────────────────┘           | |
|  |  ┌─ 🐻 Bear Researcher ──────────────────────┐           | |
|  |  │ "估值已高于历史均值..."                       │           | |
|  |  └──────────────────────────────────────────┘           | |
|  |                                                           | |
|  |  ## 分析结论                                               | |
|  |  **信号**: 买入 | **置信度**: 0.78                          | |
|  |  ...Dashboard...                                          | |
|  |                                                           | |
|  |  [查看完整报告] [在K线标注] [继续追问 ↗ 侧边栏]            | |
|  +----------------------------------------------------------+ |
|  |  输入追问...                              [发送] [停止]    | |
|  +----------------------------------------------------------+ |
+--------------------------------------------------------------+
```

### D1: 侧边栏 Chat Panel (轻量对话)

#### 定位

- **常驻侧边栏**，在任何标签页（Chart/News/Report）时都可直接使用
- 处理快速问答、自由聊天、quick 分析、单 Agent 查询
- 作为 Agent Window 的入口（"帮我深度分析 600519" → 自动建议打开 Agent Window）
- standard 模式可在侧边栏运行（作为增强模式，不含辩论）

#### 支持的模式

| 模式 | 说明 | 后端路由 |
|------|------|---------|
| **自由对话** (默认) | 普通 Chat，无 Agent pipeline | `/agent/chat/stream` (mode=chat) |
| **快速分析** | 简化结论，侧边栏内展示 | `/agent/chat/stream` (mode=quick) |
| **标准分析** | tech → intel → decision，较详细 | `/agent/chat/stream` (mode=standard) |
| **单 Agent** | 指定 agent_id 回答 | `/agent/chat/stream` + `agent_id` |

#### 智能升级提示

当侧边栏检测到以下场景时，自动在回复末尾显示 **[🚀 启动深度分析]** 按钮：
- 用户明确要求 "详细分析" / "深度分析" / "全面分析"
- quick/standard 模式分析完成后，置信度偏低 (< 0.6)
- 用户追问需要辩论视角 ("多空怎么看？")

#### 新增文件

| 文件 | 用途 |
|------|------|
| `src/renderer/src/components/sidebar/ChatPanel.vue` | 侧边栏 Chat 主组件 |
| `src/renderer/src/components/sidebar/ChatMessageList.vue` | 消息列表 (轻量) |
| `src/renderer/src/components/sidebar/ChatMessage.vue` | 单条消息 (精简 Markdown) |
| `src/renderer/src/components/sidebar/ChatInput.vue` | 输入框 + 模式选择 |
| `src/renderer/src/components/sidebar/SessionList.vue` | 会话切换列表 |
| `src/renderer/src/composables/useChat.ts` | Chat 状态管理 composable |
| `src/renderer/src/composables/useChatStream.ts` | SSE 流式处理 composable |
| `src/renderer/src/service/chatService.ts` | Chat API 封装 + SSE 消费 |

#### 与现有侧边栏的关系

- **替代** `index.js` 中的 `initAgentChat()` 原生 DOM 实现
- 复用现有侧边栏容器 (已有的 `#agent-panel` 区域)
- 保留现有会话 API 兼容 (`/api/v1/agent/chat/sessions`)

### D2: Agent Window (深度分析)

#### 定位

- **独立弹出窗口** (Electron BrowserWindow)，参考 VS Code Agent 面板
- 处理完整 Agent 集群分析 (full/specialist)、多角色辩论可视化、Plan 模式
- 辩论模式（Bull/Bear + Risk 三方讨论）**仅在此窗口可用**
- 需要 ≥600px 宽度展示 AgentProgress + Debate 面板 + Dashboard
- 分析完成后可关闭，结果同步到侧边栏会话

#### 触发方式

| 触发 | 说明 |
|------|------|
| **左上角 [🤖] 按钮** | 全局 Agent 启动按钮，位于侧边栏开关按钮旁 |
| 侧边栏消息中 [🚀 启动深度分析] | 基于当前对话上下文跳转 |
| 快捷键 `Ctrl+Shift+A` / `Cmd+Shift+A` | 全局快捷键 |
| K 线图右键菜单 → "AI 分析此标的" | 从图表触发 |
| 侧边栏智能建议 | 检测到复杂需求时自动建议 |

#### 支持的模式

| 模式 | 前端行为 | 后端路由 | 辩论 |
|------|---------|---------|------|
| **standard** | Agent 进度条 (无辩论) | `/agent/chat/stream` (mode=standard) | ❌ |
| **full** (默认) | 完整进度 + 辩论可视化 | `/agent/chat/stream` (mode=full) | ✅ Bull/Bear + Risk |
| **specialist** | 完整进度 + 策略专家 | `/agent/chat/stream` (mode=specialist) | ✅ Bull/Bear + Risk |
| **plan** | 先展示计划 → 确认 → 执行 | `/agent/chat/stream` (mode=plan) | ✅ (执行阶段) |
| **对比分析** | 多标的并排 | 多次调用 + 前端拼装 | ✅ |

#### 新增文件

| 文件 | 用途 |
|------|------|
| `src/renderer/agent-window.html` | Agent Window 入口 HTML |
| `src/renderer/src/agentWindow.ts` | Agent Window 入口 JS |
| `src/renderer/src/AgentWindow.vue` | Agent Window 主视图 |
| `src/renderer/src/components/agent/AgentProgress.vue` | Agent 管线进度可视化 |
| `src/renderer/src/components/agent/DebatePanel.vue` | 辩论过程可视化 (Bull/Bear 对话面板) |
| `src/renderer/src/components/agent/RiskDebatePanel.vue` | 风险三方讨论可视化 |
| `src/renderer/src/components/agent/ThinkingBlock.vue` | 折叠式思考过程 |
| `src/renderer/src/components/agent/ToolCallCard.vue` | 工具调用卡片 |
| `src/renderer/src/components/agent/StreamRenderer.vue` | SSE 流式文本渲染 |
| `src/renderer/src/components/agent/PlanCard.vue` | Plan 模式确认卡片 |
| `src/renderer/src/components/agent/DashboardResult.vue` | 分析结果 Dashboard |

#### Electron 窗口管理

```typescript
// src/main/index.js — Agent Window 管理

function openAgentWindow(options: { symbol?: string; mode?: string; sessionId?: string }) {
  const agentWin = new BrowserWindow({
    width: 900,
    height: 750,
    parent: mainWindow,          // 关联主窗口
    modal: false,                // 非模态，可同时操作主窗口
    title: 'AI 深度分析',
    webPreferences: { preload: '...' }
  });
  agentWin.loadFile('agent-window.html', { query: options });
}

// IPC: 左上角按钮 / 侧边栏 → main → 打开 Agent Window
ipcMain.handle('agent:open-window', (event, options) => openAgentWindow(options));

// IPC: Agent Window 分析完成 → 同步结果到侧边栏
ipcMain.handle('agent:sync-result', (event, { sessionId, summary }) => {
  mainWindow.webContents.send('sidebar:agent-result', { sessionId, summary });
});
```

### D3: 左上角 Agent 启动按钮

#### 设计

```
+---+---+
| ≡ | 🤖|    ← 左上角工具栏
+---+---+
  |    |
  |    └── Agent Window 启动按钮 (新增)
  └─────── 侧边栏开关按钮 (已有)
```

#### 行为

| 状态 | 点击行为 |
|------|---------|
| Agent Window 未打开 | 打开新的 Agent Window（空白状态，等待输入标的） |
| Agent Window 已打开 | 聚焦到已有的 Agent Window |
| Agent Window 正在分析中 | 聚焦到已有窗口，显示当前进度 |

#### 实现

```typescript
// src/main/index.js 或 src/main/agentWindow.js

let agentWindow: BrowserWindow | null = null;

function toggleAgentWindow() {
  if (agentWindow && !agentWindow.isDestroyed()) {
    agentWindow.focus();
  } else {
    agentWindow = openAgentWindow({});
    agentWindow.on('closed', () => { agentWindow = null; });
  }
}

// 左上角按钮 IPC
ipcMain.handle('agent:toggle-window', () => toggleAgentWindow());
```

#### 前端按钮位置

在主窗口的标题栏/工具栏区域，紧邻已有的侧边栏开关按钮：

```vue
<!-- src/renderer/src/components/TitleBar.vue 或类似位置 -->
<div class="title-bar-left">
  <button @click="toggleSidebar" title="切换侧边栏">≡</button>
  <button @click="openAgentWindow" title="AI 深度分析 (Ctrl+Shift+A)" class="agent-btn">
    🤖
  </button>
</div>
```

### D4: 侧边栏 ↔ Agent Window 联动

| 场景 | 流程 |
|------|------|
| 侧边栏 → Agent Window | 用户点击 [🚀 启动深度分析] → IPC 打开 Agent Window，传入标的/上下文 |
| 左上角按钮 → Agent Window | 点击 [🤖] → 打开/聚焦 Agent Window |
| Agent Window → 侧边栏 | 分析完成 → 摘要同步回侧边栏会话（"✅ 600519 分析完成：买入 0.78"）|
| Agent Window → K 线图 | 点击 [在K线标注] → IPC 通知 Chart 标签添加标注 |
| 侧边栏追问 | Agent Window 结果中点击 [继续对话 ↗] → 焦点切到侧边栏，带上下文 |

#### 共享会话

- 侧边栏和 Agent Window **共享同一个 session_id**
- Agent Window 的分析结果作为 assistant 消息存入会话
- 用户可在侧边栏继续追问 Agent Window 的分析结果
- Agent Window 中的辩论过程摘要也存入会话历史（供后续追问参考）

### D5: Plan 模式 (Agent Window 内)

```
用户: "分析一下贵州茅台"
  ↓ mode=plan (在 Agent Window 中)
AI: 生成分析计划:
  1. 获取近30日K线 + 技术指标
  2. 搜索近期新闻 + 公告
  3. Bull/Bear 辩论 (2轮)
  4. 风险三方讨论
  5. 综合决策

  [执行计划] [修改] [取消]
  ↓ 用户点击执行
  正常 Agent pipeline 执行 (full/specialist 模式)...
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

### D6: 会话管理

#### 功能

- 新建对话 / 切换对话 / 删除对话
- 自动从第一条消息生成标题
- 按标的/日期筛选
- 导出对话为 Markdown
- 会话中标记哪些消息来自 Agent Window 深度分析（带辩论摘要标志）

#### API (已有)

```
GET  /api/v1/agent/chat/sessions         → 会话列表
GET  /api/v1/agent/chat/sessions/{id}    → 历史消息
DELETE /api/v1/agent/chat/sessions/{id}  → 删除
```

### D7: 快捷操作

| 操作 | 位置 | 效果 |
|------|------|------|
| 在 K 线标注 | Agent Window 结果中 | IPC → Chart 标签添加标注 |
| 深度分析 | 侧边栏消息中 | 打开 Agent Window + 传入上下文 |
| 追问细节 | Agent Window 阶段卡片 | 在 Agent Window 内追问 |
| `/mode` 命令 | 侧边栏输入框 | 切换侧边栏对话模式 (chat/quick/standard) |
| 查看原始数据 | Agent Window 折叠展开 | 展示 Agent 的 raw_data JSON |
| 查看辩论详情 | Agent Window 辩论面板 | 展开/折叠 Bull/Bear 完整论据 |

### D8: 后端新增/修改

| 文件 | 修改 |
|------|------|
| `backend/api/v1/endpoints/agent.py` | 新增 SSE event: `stage_start`/`stage_done`/`debate_round`/`risk_debate` |
| `backend/src/agent/orchestrator.py` | progress_callback 发送辩论/风险讨论阶段事件 |
| `backend/api/v1/endpoints/agent.py` | 新增 `mode` 参数支持 (plan/chat/quick/standard/full/specialist) |
| `backend/api/v1/endpoints/agent.py` | 新增 `agent_id` 参数 (单 Agent 模式) |
| `backend/src/agent/plan_mode.py` | PlanModeHandler 新增文件 |

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

### Step 1: 侧边栏 Chat Panel (D1)

| # | 任务 | 产出 | 预估 |
|---|------|------|------|
| 1.1 | ChatPanel.vue 侧边栏主组件 (替代 initAgentChat DOM) | 侧边栏 Chat | M |
| 1.2 | ChatMessageList + ChatMessage 组件 (精简 Markdown) | 消息渲染 | M |
| 1.3 | ChatInput 组件 (输入框 + 模式选择 chat/quick/standard/single) | 输入控件 | S |
| 1.4 | useChatStream composable (SSE 消费) | 流式处理核心 | M |
| 1.5 | chatService.ts (API 封装 + SSE) | HTTP + SSE 封装 | S |
| 1.6 | SessionList 组件 (会话切换) | 会话列表 | S |
| 1.7 | 集成到现有侧边栏 #agent-panel 区域 | 替换旧 DOM | S |
| 1.8 | 智能升级提示 (检测复杂需求 → 建议打开 Agent Window) | 交互优化 | S |
| 1.9 | 移除 index.js 中 initAgentChat() 旧代码 | 清理 | S |

### Step 2: Agent Window + 左上角入口 (D2+D3)

| # | 任务 | 产出 | 预估 |
|---|------|------|------|
| 2.1 | agent-window.html + agentWindow.ts 入口 | 新窗口 | S |
| 2.2 | AgentWindow.vue 主视图 (含模式选择: standard/full/specialist/plan) | Agent 窗口页面 | M |
| 2.3 | AgentProgress 组件 (阶段进度可视化) | 管线进度 | M |
| 2.4 | DebatePanel 组件 (Bull/Bear 辩论可视化) | 辩论面板 | M |
| 2.5 | RiskDebatePanel 组件 (风险三方讨论可视化) | 风险面板 | M |
| 2.6 | ThinkingBlock + ToolCallCard 组件 | 思考过程 | M |
| 2.7 | StreamRenderer 组件 (流式 Markdown) | 流式文本 | M |
| 2.8 | DashboardResult 组件 (分析结果展示) | 结果 Dashboard | M |
| 2.9 | Electron BrowserWindow 管理 (openAgentWindow / toggleAgentWindow) | main/index.js | S |
| 2.10 | **左上角 [🤖] Agent 启动按钮** (紧邻侧边栏开关按钮) | TitleBar 修改 | S |
| 2.11 | 快捷键注册 Ctrl+Shift+A / Cmd+Shift+A | 全局快捷键 | S |

### Step 3: 后端 SSE 增强 (D1+D2 配套)

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | agent.py 新增 stage_start/stage_done/debate_round/risk_debate 事件 | API 增强 |
| 3.2 | orchestrator progress_callback 发送辩论/风险讨论阶段事件 | 辩论/风险阶段事件 |
| 3.3 | 新增 `mode` 请求参数 (chat/quick/standard/full/specialist/plan) | 模式路由 |
| 3.4 | 新增 `agent_id` 参数 (单 Agent 模式) | 单 Agent 路由 |
| 3.5 | 模式权限校验 (full/specialist/plan 仅 Agent Window 可调用) | 安全约束 |

### Step 4: 侧边栏 ↔ Agent Window 联动 (D4)

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | IPC: 左上角按钮 / sidebar → main → Agent Window (打开 + 传参) | 窗口通信 |
| 4.2 | IPC: Agent Window → main → sidebar (结果同步) | 结果回传 |
| 4.3 | 共享 session_id 机制 | 会话一致性 |
| 4.4 | K 线图右键菜单 "AI 分析此标的" → 打开 Agent Window | 图表集成 |
| 4.5 | Agent Window 辩论摘要同步到侧边栏会话 | 辩论结果共享 |

### Step 5: K 线信号标注 (B1-B3)

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | annotation.ts 类型定义 | 数据模型 |
| 5.2 | annotationService.ts (CRUD + 持久化) | 服务层 |
| 5.3 | KLineChart 标注渲染集成 | Chart.vue 修改 |
| 5.4 | IPC: Agent Window → Main → Chart 标注联动 | 标注通信 |
| 5.5 | 标注管理面板 (显示/隐藏/删除) | Chart.vue 子组件 |

### Step 6: 跨市场时间轴 (B4)

| # | 任务 | 产出 |
|---|------|------|
| 6.1 | tradingHours.ts (时段配置) | 服务层 |
| 6.2 | KLineChart x 轴非交易时段折叠 | Chart 配置 |
| 6.3 | 标的切换时自动适配时区 | Chart.vue 逻辑 |

### Step 7: Plan 模式 (D5)

| # | 任务 | 产出 |
|---|------|------|
| 7.1 | PlanModeHandler 后端实现 | 新增文件 |
| 7.2 | PlanCard 前端组件 (Agent Window 内) | 确认/修改/取消 |
| 7.3 | 前端确认 → 触发执行流 (full/specialist pipeline) | chatService 扩展 |

### Step 8: 新闻采集扩展 (N1-N3)

| # | 任务 | 产出 |
|---|------|------|
| 8.1 | XueqiuCrawler (雪球) | 新 crawler |
| 8.2 | CLSCrawler (财联社) | 新 crawler |
| 8.3 | ReutersCrawler (Reuters RSS) | 新 crawler |
| 8.4 | 新闻实时推送 (WebSocket news channel) | realtime_ws 扩展 |
| 8.5 | 前端 NewsFilter 源筛选 + 实时推送 | 组件增强 |
| 8.6 | 新闻 → 侧边栏 Chat 拖拽关联 | 交互增强 |

### Step 9: 快捷操作 (D7)

| # | 任务 | 产出 |
|---|------|------|
| 9.1 | [在K线标注] 按钮 + IPC 触发 (Agent Window) | 结果联动 |
| 9.2 | `/mode` 斜杠命令解析 (侧边栏，限 chat/quick/standard) | ChatInput 逻辑 |
| 9.3 | Agent 阶段点击追问 (Agent Window) | AgentProgress 交互 |
| 9.4 | [继续对话 ↗ 侧边栏] 焦点切换 | 跨窗口联动 |
| 9.5 | 辩论面板 Bull/Bear 论据展开/折叠 | DebatePanel 交互 |

### Step 10: 旧入口下线

| # | 任务 | 产出 |
|---|------|------|
| 10.1 | 验证侧边栏 Chat Panel 完全覆盖 initAgentChat 功能 | 功能验证 |
| 10.2 | 验证 Agent Window 完全覆盖 StockAnalysis.vue 功能 | 功能验证 |
| 10.3 | 移除 StockAnalysis.vue + stock-analysis.html | 代码清理 |
| 10.4 | 移除 index.js 中 initAgentChat 相关 DOM 和样式 | 代码清理 |

---

## 技术选型

| 需求 | 选型 | 理由 |
|------|------|------|
| Markdown 渲染 | `markdown-it` + `highlight.js` | 已有依赖，轻量 |
| 虚拟滚动 | Agent Window 中使用 `vue-virtual-scroller` | 长分析结果性能；侧边栏无需 |
| SSE 消费 | 原生 `EventSource` + composable 封装 | 无需额外依赖 |
| 流式文本 | requestAnimationFrame + 增量 DOM | 打字机效果 |
| Agent Window | Electron `BrowserWindow` (child) | 独立进程，不影响主窗口 |
| 窗口通信 | `ipcMain` / `ipcRenderer` | Electron 标准方案 |
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

// 侧边栏 (mode=chat/quick/standard): 仅经历 connecting → thinking → generating → done
//   (standard 可能有 executing 阶段，但不含 debating)
// Agent Window (mode=full/specialist): 完整状态流转，含 executing + debating
```

### SSE 事件 → UI 层级映射

```typescript
// useChatStream.ts — 侧边栏和 Agent Window 共用，按 context 决定渲染粒度

interface ChatStreamEvent {
  type: 'thinking' | 'tool_start' | 'tool_done' | 'stage_start' | 'stage_done'
      | 'parallel_start' | 'debate_round' | 'generating' | 'done' | 'error';
  data: Record<string, any>;
}

// 侧边栏处理:
// thinking   → 简短 "思考中..." 指示
// stage_start→ (standard 模式) 简短阶段名显示
// generating → 流式文字
// done       → 最终消息 + [🚀 启动深度分析] 按钮 (智能推荐)
// (debate_round/risk_debate 事件在侧边栏中忽略，不会出现)

// Agent Window 处理:
// thinking      → ThinkingBlock (折叠式详情)
// tool_start    → ToolCallCard (loading 状态)
// tool_done     → ToolCallCard (完成, 显示摘要)
// stage_start   → AgentProgress (更新当前阶段)
// stage_done    → AgentProgress (标记完成 + 耗时)
// parallel_start→ AgentProgress (并行指示)
// debate_round  → DebatePanel (辩论轮次 + Bull/Bear 论据实时显示)
// risk_debate   → RiskDebatePanel (风险三方讨论可视化)
// generating    → StreamRenderer (流式文字)
// done          → DashboardResult (完整结果展示)
// error         → 错误提示
```

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| **双层入口** (侧边栏 + Agent Window) | 参考 VS Code Copilot：轻量交互不遮挡工作区，重量分析独占焦点 |
| **辩论模式仅限 Agent Window** | Bull/Bear + Risk 辩论耗时长、过程复杂，需要专用进度面板和对话可视化 |
| **左上角 Agent 启动按钮** | 参考 VS Code 布局，全局入口不依赖侧边栏状态，随时可用 |
| 侧边栏为日常 AI 入口 | 随时可用，不需切换标签；降低使用门槛 |
| Agent Window 为独立 BrowserWindow | 需要 ≥600px 宽度；不影响主窗口标签布局；可同时操作 |
| 侧边栏和 Agent Window 共享 session_id | 会话连续性；分析结果可在侧边栏追问 |
| 侧边栏支持 standard 模式 | 作为侧边栏的增强模式，无辩论但有情报搜集，满足中等深度需求 |
| SSE (非 WebSocket) 用于 Agent 流式 | 已有成熟实现，单向推送场景够用 |
| WebSocket 仅用于实时行情 + 新闻推送 | 双向通信场景 |
| Plan 模式仅在 Agent Window 中 | 需要空间展示计划列表 + 确认交互 |
| 标注存 localStorage 为主 | 简单可靠，后续可加后端 sync |
| 不引入全局状态管理 (Pinia) | 各窗口独立进程，composable + IPC 足够 |
| 先做侧边栏再做 Agent Window | 侧边栏改造成本低（基于已有），优先交付核心体验 |
| StockAnalysis.vue 最终废弃 | Agent Window 完全覆盖其功能后移除 |

---

## 文件树预览 (Phase 4 新增)

```
src/renderer/
├─ agent-window.html                   # Agent Window 入口 HTML
├─ src/
│  ├─ agentWindow.ts                   # Agent Window 入口 JS
│  ├─ AgentWindow.vue                  # Agent Window 主视图
│  ├─ components/
│  │  ├─ sidebar/                      # 侧边栏 Chat Panel 组件
│  │  │  ├─ ChatPanel.vue             # 侧边栏 Chat 主组件
│  │  │  ├─ ChatMessageList.vue       # 消息列表 (轻量)
│  │  │  ├─ ChatMessage.vue           # 单条消息 (精简 Markdown)
│  │  │  ├─ ChatInput.vue             # 输入框 + 模式选择 (chat/quick/standard/single)
│  │  │  └─ SessionList.vue           # 会话切换列表
│  │  ├─ agent/                        # Agent Window 专属组件
│  │  │  ├─ AgentProgress.vue          # Agent 管线进度可视化
│  │  │  ├─ DebatePanel.vue            # Bull/Bear 辩论可视化 (仅 Agent Window)
│  │  │  ├─ RiskDebatePanel.vue        # 风险三方讨论可视化 (仅 Agent Window)
│  │  │  ├─ ThinkingBlock.vue          # 折叠式思考过程
│  │  │  ├─ ToolCallCard.vue           # 工具调用卡片
│  │  │  ├─ StreamRenderer.vue         # 流式 Markdown 渲染
│  │  │  ├─ PlanCard.vue               # Plan 模式确认卡片
│  │  │  └─ DashboardResult.vue        # 分析结果 Dashboard
│  │  └─ titlebar/                     # 标题栏组件
│  │     └─ AgentLaunchButton.vue      # 左上角 Agent 启动按钮 [🤖]
│  ├─ composables/
│  │  ├─ useChat.ts                    # Chat 状态管理 (侧边栏 + Agent Window 共用)
│  │  └─ useChatStream.ts             # SSE 流式处理 (共用)
│  ├─ service/
│  │  ├─ chatService.ts               # Chat API 封装 (共用)
│  │  ├─ annotationService.ts         # 标注服务
│  │  └─ tradingHours.ts              # 交易时段配置
│  └─ types/
│     └─ annotation.ts                 # 标注类型定义

src/main/
├─ agentWindow.js                      # Agent Window 窗口创建与管理 (含单例逻辑)
├─ ipc/
│  └─ agentIpc.js                      # agent:open-window / agent:toggle-window / agent:sync-result IPC

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
| 侧边栏首次响应 | ~800ms (initAgentChat) | <500ms (Vue 组件 + SSE) |
| Agent Window 打开 | N/A | <300ms (Electron BrowserWindow) |
| full 模式总延迟 | ~15-30s | 不变 (后端不变) |
| SSE 事件密度 | ~5-8 事件/分析 | ~15-20 事件 (含 stage 细粒度) |
| 前端 bundle 增量 | — | 侧边栏: +20KB / Agent Window: +50KB |
| 内存 (Agent Window) | — | <80MB (独立进程) |
| 内存 (侧边栏) | — | <10MB (轻量消息列表) |

---

## 依赖关系

```
Step 1 (侧边栏 Chat Panel) — 无外部依赖，可立即开始
  ↓
Step 2 (Agent Window) — 复用 Step 1 的 composables/service
  ↓
Step 3 (SSE 增强) — 依赖 Step 1+2 的事件消费组件
  ↓
Step 4 (侧边栏↔Agent Window 联动) — 依赖 Step 1 + Step 2
  ↓ (可并行)
Step 5 (K线标注) — 独立，可与 Step 1-4 并行
Step 6 (跨市场时间) — 独立
Step 7 (Plan 模式) — 依赖 Step 2 + Step 3
Step 8 (新闻扩展) — 独立
Step 9 (快捷操作) — 依赖 Step 4 + Step 5
Step 10 (旧入口下线) — 依赖 Step 1 + Step 2 + Step 4 全部完成
```

**建议执行顺序**: Step 1 → Step 2 → Step 3 → Step 4 → (Step 5 ∥ Step 6 ∥ Step 7 ∥ Step 8) → Step 9 → Step 10
