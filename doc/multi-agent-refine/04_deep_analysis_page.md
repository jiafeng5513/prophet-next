# 04 — 深度分析页面增强计划

> **状态: ✅ 已完成 (2026-05-24)**
>
> 已实施内容:
> - `StockAnalysis.vue`: 三栏布局(左历史+中结果+右进度), 模式切换, useChatStream 集成
> - `AnalysisSideProgress.vue`: 右侧栏实时进度(阶段/辩论/风险/思考)
> - `FollowUpInput.vue`: 追问输入(快捷问题+自由输入)
> - `AnalysisRadar.vue`: 纯 SVG 多维雷达图
> - `AnalysisExport.vue`: 导出(Markdown/复制/JSON)
> - `CompareAnalysis.vue`: 对比分析表格
> - `AgentWindow.vue`: 轻量化为浮动对话助手

## 一、现状分析

### 当前有两个分析入口

| 组件 | 入口 | 能力 | 问题 |
|------|------|------|------|
| `StockAnalysis.vue` | 主标签页 "AI 分析" | 搜索→分析→展示结果+历史 | 无辩论/进度/模式切换 |
| `AgentWindow.vue` | 独立弹窗 (Ctrl+Shift+A) | 全功能: 模式/进度/辩论/Dashboard | 弹窗体验差，与主应用割裂 |

### StockAnalysis.vue 现有功能
- 左侧: 分析历史列表 (task_id + stock_code + status)
- 右侧: 搜索栏 + 结果展示
- 支持模式选择（但仅 quick/standard/full）
- 结果展示: 渲染 Dashboard JSON 为格式化卡片

### AgentWindow.vue 独有功能
- Agent 执行进度 (`AgentProgress` 组件)
- 辩论面板 (`DebatePanel` 组件)
- 风险讨论面板 (`RiskDebatePanel` 组件)
- 思考过程 (`ThinkingBlock` 组件)
- 工具调用展示 (`ToolCallCard` 组件)
- 流式渲染 (`StreamRenderer` 组件)
- 计划卡片 (`PlanCard` 组件)
- 交互式输入 (`ChatInput` 组件)

---

## 二、重构目标

将 AgentWindow 的能力**整合到 StockAnalysis 主标签页**，提供统一的深度分析体验:

1. **沉浸式分析流程** — 从搜索到结果在一个页面完成
2. **实时分析进度** — 看到每个 Agent 阶段的执行状态
3. **辩论可视化** — 多空辩论和风险讨论过程可展开查看
4. **多维结果展示** — Dashboard + 雷达图 + 风险矩阵 + 时间轴
5. **追问与对比** — 基于分析结果继续追问，或对比多个标的

---

## 三、页面布局设计

### 3.1 三栏式布局

```
┌─────────────┬──────────────────────────┬──────────────────┐
│   左侧栏     │       主内容区             │   右侧栏          │
│  (240px)    │    (flex: 1)             │  (300px, 可折叠)  │
│             │                          │                  │
│ 分析历史     │  ┌──────────────────┐    │ 实时进度          │
│ • 600519    │  │ 搜索栏 + 模式选择  │    │ • Technical ✅   │
│ • AAPL      │  └──────────────────┘    │ • Intel ✅        │
│ • BTC-USDT  │                          │ • Risk 🔄         │
│             │  ┌──────────────────┐    │ • Debate ⏳       │
│ [按时间]     │  │                  │    │   - Round 1/2     │
│ [按标的]     │  │   分析结果展示     │    │ • Decision ⏳     │
│             │  │                  │    │                  │
│             │  │   Dashboard      │    │ 辩论详情          │
│             │  │   + 图表         │    │ 📈 多方论点       │
│             │  │   + 辩论摘要     │    │ 📉 空方论点       │
│             │  │   + 风险评估     │    │ ⚖️ 裁决          │
│             │  │                  │    │                  │
│             │  └──────────────────┘    │ 追问输入框        │
│             │                          │ [基于此结果提问]   │
└─────────────┴──────────────────────────┴──────────────────┘
```

### 3.2 主内容区 — 分析结果展示

结果区使用**卡片式布局**，可折叠/展开:

```
┌─ 核心结论 ──────────────────────────────────────────┐
│ 🟢 贵州茅台 — 强烈看多                               │
│ 量价齐升突破前高，板块轮动到白酒，建议逢低布局         │
│ 信号: 买入 | 信心: 85% | 时效: 本周内                 │
└────────────────────────────────────────────────────────┘

┌─ 数据仪表盘 ─────────────────────────────────────────┐
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │ 趋势评分 │ │ 量能状态 │ │ 筹码结构 │ │ 情绪指数 │    │
│  │   78    │ │  放量    │ │ 获利92% │ │  偏贪婪  │    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│                                                       │
│  [迷你K线图 — 标注买卖信号点]                          │
└────────────────────────────────────────────────────────┘

┌─ 作战计划 ───────────────────────────────────────────┐
│  理想买入: ¥1850  |  止损: ¥1780  |  止盈: ¥2050     │
│  建议仓位: 30%    |  入场策略: 分批建仓              │
│                                                       │
│  Action Checklist:                                    │
│  ☐ 确认日线收盘站稳1860                              │
│  ☐ 观察明日量能是否维持                              │
│  ☐ 关注板块联动效应                                  │
└────────────────────────────────────────────────────────┘

┌─ 多空辩论 (可折叠) ──────────────────────────────────┐
│  📈 多方: 量价突破+板块轮动+北向资金加仓 → 强买入     │
│  📉 空方: 高位筹码松动+大盘滞涨+估值偏高 → 谨慎      │
│  ⚖️ 裁决: 短期多方占优，但需控制仓位防范系统性风险    │
│                                                       │
│  [展开查看完整辩论过程 ▼]                             │
└────────────────────────────────────────────────────────┘

┌─ 风险矩阵 (可折叠) ──────────────────────────────────┐
│  激进视角: 可重仓 — 趋势确认+催化剂明确               │
│  保守视角: 轻仓试探 — 估值不便宜+减持预期             │
│  中性裁决: 中等仓位 (20-30%)                          │
│                                                       │
│  风险因子:                                            │
│  • 系统性: ⚠️ 中  (大盘高位震荡)                      │
│  • 流动性: ✅ 低  (日均成交>10亿)                     │
│  • 事件性: ⚠️ 中  (季报窗口临近)                      │
└────────────────────────────────────────────────────────┘

┌─ 市场环境 (可折叠) ──────────────────────────────────┐
│  大盘: 上证 3320 (+0.5%) | 创业板 2180 (+0.8%)       │
│  板块: 白酒 +2.3% (排名 3/68) | 消费 +1.1%          │
│  情绪: 偏乐观 | 北向: +35亿                          │
└────────────────────────────────────────────────────────┘
```

---

## 四、新增组件规划

### 4.1 分析进度组件 (AnalysisProgress.vue)

```vue
<template>
  <div class="analysis-progress">
    <div v-for="stage in stages" :key="stage.name" class="progress-stage">
      <span class="stage-icon">{{ stageIcon(stage.status) }}</span>
      <span class="stage-name">{{ stage.label }}</span>
      <span class="stage-time" v-if="stage.duration">{{ stage.duration }}s</span>
    </div>
    <!-- 辩论进度（展开式） -->
    <div v-if="debateRounds.length" class="debate-progress">
      <div v-for="round in debateRounds" :key="round.num">
        Round {{ round.num }}/{{ round.total }}: {{ round.status }}
      </div>
    </div>
  </div>
</template>
```

### 4.2 雷达图组件 (AnalysisRadar.vue)

展示多维度评分的雷达图:
- 趋势强度 (0-100)
- 量能配合 (0-100)
- 情报面 (0-100)
- 风险评级 (0-100, 反转)
- 策略匹配 (0-100)
- 资金趋势 (0-100)

技术: 使用 ECharts 或 Chart.js 的 radar 类型。

### 4.3 辩论详情组件 (DebateDetail.vue)

可展开的辩论过程展示:
- 时间轴形式展示每一轮
- 多方/空方/裁决分色显示
- 支持折叠（默认只显示最终裁决）

### 4.4 追问输入组件 (FollowUpInput.vue)

基于当前分析结果的追问:
```
预设快捷问题:
- "如果大盘下跌3%，这个结论会变吗？"
- "对比同板块其他龙头"
- "最近的减持公告有什么影响？"
- "帮我生成详细的交易计划"

[自由输入: 输入你的追问...]
```

追问发送时携带当前分析的 context（session_id + task_id）。

### 4.5 对比分析组件 (CompareAnalysis.vue)

支持多标的对比:
- 横向对比表格（A标的 vs B标的 各维度评分）
- 叠加雷达图
- 同板块标的自动推荐

---

## 五、实现步骤

### Phase 3.1: 基础整合 (将 AgentWindow 组件迁移到 StockAnalysis)

| # | 任务 | 说明 |
|---|------|------|
| 1 | 迁移 AgentProgress | 右侧栏展示实时进度 |
| 2 | 迁移 StreamRenderer | 支持流式渲染结果 |
| 3 | 迁移 DebatePanel/RiskDebatePanel | 可折叠式展示辩论 |
| 4 | 页面布局改为三栏式 | 左(历史) + 中(结果) + 右(进度/辩论) |
| 5 | 搜索栏增加模式选择 | 简化为 quick/deep 两个按钮 |

### Phase 3.2: 结果展示增强

| # | 任务 | 说明 |
|---|------|------|
| 6 | Dashboard 卡片化重构 | 分区域可折叠展示 |
| 7 | 新增 AnalysisRadar | 多维雷达图 |
| 8 | 新增辩论摘要区 | 显示 debate_summary 新字段 |
| 9 | 新增风险矩阵区 | 显示 risk_assessment 新字段 |
| 10 | 新增市场环境区 | 显示 market_context 新字段 |

### Phase 3.3: 交互增强

| # | 任务 | 说明 |
|---|------|------|
| 11 | 追问功能 | FollowUpInput + 上下文传递 |
| 12 | 对比分析 | CompareAnalysis 组件 |
| 13 | 分析结果导出 | PDF / Markdown / 分享链接 |
| 14 | K线图标注联动 | 分析结果的买卖点标注到 Chart 标签页 |

### Phase 3.4: AgentWindow 处理

| # | 任务 | 说明 |
|---|------|------|
| 15 | 评估是否保留 AgentWindow | 如 StockAnalysis 已覆盖全部能力则移除 |
| 16 | 或改为"浮动助手" | 悬浮窗形式，快速对话用途 |

---

## 六、技术实现要点

### 6.1 SSE 流式数据增强

当前 SSE 事件类型:
```
data: {"type": "thinking", "content": "..."}
data: {"type": "tool_call", "name": "...", "args": {...}}
data: {"type": "tool_result", "name": "...", "result": {...}}
data: {"type": "content", "content": "..."}
data: {"type": "stage_complete", "stage": "technical", "duration": 3.2}
data: {"type": "debate_round", "round": 1, "bull": "...", "bear": "..."}
data: {"type": "done", "dashboard": {...}}
```

需要确保:
- `debate_round` 事件包含 `type` 字段（当前缺失）
- 新增 `risk_debate_round` 事件类型
- `stage_complete` 事件包含 stage 的 opinion 摘要

### 6.2 组件通信

```
StockAnalysis.vue (容器)
├── SearchBar.vue (输入 + 模式选择)
├── AnalysisContent.vue (主内容)
│   ├── CoreConclusion.vue
│   ├── DataDashboard.vue
│   ├── BattlePlan.vue
│   ├── DebateSummary.vue (可折叠)
│   ├── RiskMatrix.vue (可折叠)
│   └── MarketContext.vue (可折叠)
├── SideProgress.vue (右侧栏)
│   ├── AnalysisProgress.vue
│   ├── DebateDetail.vue
│   └── FollowUpInput.vue
└── HistoryPanel.vue (左侧栏)
```

使用 Pinia store 管理:
- `analysisStore` — 分析状态、结果数据
- SSE 事件 → store actions → 组件响应式更新

### 6.3 响应式设计

- 小屏幕: 右侧栏折叠为底部抽屉
- 中屏幕: 左侧栏折叠，右侧保留
- 大屏幕: 三栏全部展示
