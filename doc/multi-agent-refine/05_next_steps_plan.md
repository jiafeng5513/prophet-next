# 05 — 多 Agent 系统下一步开发计划

## 一、修复分析报告不显示问题（P0 优先）
- 检查后端 DecisionAgent 的 `done` 事件，确保始终携带 dashboard 字段
- 前端 StockAnalysis.vue 增加降级逻辑：若无 dashboard 但有 content，仍用 StreamRenderer 渲染 markdown
- 补充异常提示，便于定位后端输出问题

## 二、入口收敛与能力迁移（P1）
### 目标
- 仅保留两个入口：Agent Window（全功能）、侧边栏（简易）
- 市场分析页能力迁移至 Agent Window，后续可废弃

### 步骤
1. Agent Window 增加历史记录（SessionList）、雷达图（AnalysisRadar）、导出（AnalysisExport）、对比分析（CompareAnalysis）等组件
2. 市场分析页入口跳转至 Agent Window
3. 侧边栏仅保留 chat/quick 模式，未来扩展编程助手等

## 三、Skill 默认策略中性化（P2）
- 修改 backend/strategies/bull_trend.yaml，去除 default_router: true
- router.py 仅在检测到 trending_up 时自动选择 bull_trend
- defaults.py 默认仅注入中性基线策略（无方向性）
- 前端 skill 选择 UI 增加“无偏见”提示

## 四、丰富分析报告内容（P3）
- DashboardResult.vue 增加：
  - K线/蜡烛图标注（买卖点）
  - 多策略对比表格
  - 详细指标数值表
  - 关联新闻与情绪可视化
- 后端 DecisionAgent 输出结构补充图表/表格所需字段
- 设计前后端数据协议，兼容老版本

## 五、优先级建议
1. P0：修复报告显示
2. P1：入口收敛与能力迁移
3. P2：Skill中性化
4. P3：报告丰富化

---
> 本计划 P0-P3 由 Copilot 2026-05-26 生成，已完成。

---

# 06 — 分析报告内容规范化计划（P4）

## 背景与问题

当前三种模式（对话 chat / 快速 quick / 深度 deep）的分析报告内容不一致：
- 某些字段依赖 LLM 自觉输出，不保证每次都包含
- 多空辩论 / 风险辩论仅 deep 模式触发，但前端无 graceful 降级
- SSE 实时辩论事件存在 type 字段缺失 bug，前端无法正确接收
- 后端 `_normalize_dashboard_payload` 未强制填充所有 dashboard 字段

---

## 一、各模式实际运行的 Agent 链

| 项目 | chat | quick | deep |
|------|------|-------|------|
| 后端实际 mode | quick（映射） | quick | deep |
| Technical Agent | ✅ | ✅ | ✅ |
| Intel Agent | ✅ | ✅ | ✅ |
| Risk Agent | ❌ | ❌ | ✅ |
| Bull/Bear 辩论 | ❌ | ❌ | ✅（需预算 >30s） |
| Risk 辩论 | ❌ | ❌ | ✅（需预算 >30s） |
| Skill Agent(s) | ❌ | ❌ | ✅（路由器选择 ≤3） |
| Decision Agent | ✅ | ✅ | ✅ |
| response_mode | dashboard(首次) / chat(追问) | dashboard(首次) / chat(追问) | dashboard(首次) / chat(追问) |

## 二、DashboardResult.vue 当前可渲染的全部区块

| 区块 | 显示条件 | 数据字段 | 实际可用模式 |
|------|---------|---------|-------------|
| 信号 + 置信度 | `signal \|\| confidence` | `signal`, `confidence` | 全部 |
| 摘要 | `summary \|\| analysis_summary` | `summary` | 全部 |
| 📈 综合评分 | `sentiment_score != null` | `sentiment_score` | 全部（LLM 不保证） |
| ✅ 关键要点 | `key_points.length` | `key_points[]` | 全部（LLM 不保证） |
| 🎯 操作建议 | `operation_advice` | `operation_advice{no_position, has_position, entry_price, stop_loss, take_profit}` | 全部（LLM 不保证） |
| 📋 指标数据 | `dashboard` 子对象 | `dashboard{}` 嵌套 | 全部（LLM 不保证） |
| 📊 市场环境 | `market_context` | `market_context{index_trend, sector_strength, market_sentiment}` | 全部（Intel Agent 需调工具） |
| ⚔️ 多空辩论 | `debate_summary` | `debate_summary{bull_core_thesis, bear_core_thesis, manager_verdict, confidence_shift}` | **仅 deep**（且 LLM 不保证输出） |
| 🛡️ 风险评估 | `risk_assessment` | `risk_assessment{aggressive_view, conservative_view, verdict, max_acceptable_position}` | **仅 deep**（且 LLM 不保证输出） |
| 🎯 策略评估 | `skill_opinions?.length` | `skill_opinions[]{skill_name, signal, confidence, key_observation}` | **仅 deep** |
| ⚠️ 风险警告 | `risk_warning` | `risk_warning` | 全部（LLM 不保证） |
| 📰 相关新闻 | `intelligence.key_news.length` | `intelligence.key_news[]{title, impact, url}` | 全部（需 Intel 搜索成功） |
| 📍 操作按钮 | 始终 | — | 全部 |

## 三、当前已确认的问题

### 3.1 SSE 辩论事件 type 缺失（Bug）
- **现象**: 前端看不到实时辩论过程
- **原因**: `debate.py` 中 `progress_callback({"stage": "debate", ...})` 未设 `"type"` 字段
- **前端期望**: `event.type === "debate_round"` / `"risk_debate"`
- **修复**: debate coordinator 发射事件时加 `"type": "debate_round"` / `"type": "risk_debate"`

### 3.2 Dashboard 字段不确定性
- **现象**: 同一模式多次分析，有时有 `debate_summary`，有时没有
- **原因**: DecisionAgent prompt 说 "include when data available"，但 LLM 不保证输出
- **修复方向**: orchestrator 后处理时强制从 ctx 数据注入缺失字段

### 3.3 模式映射混乱
- **现象**: 用户选 "对话" 模式，实际执行与 "快速" 模式完全相同
- **原因**: `MODE_MAPPING` 将 `"chat"` 映射为自身，但 VALID_MODES 只有 `("quick","deep")`，fallback 到 quick
- **建议**: 明确 chat 模式的定位——是自由对话（不出 dashboard）还是简化版 quick

---

## 四、规范化方案：统一各模式的报告内容

### 4.1 所有模式共有的基础区块（必须出现）

| 区块 | 说明 |
|------|------|
| 信号 + 置信度 | buy/hold/sell + 百分比 |
| 综合评分（仪表盘） | 0-100 sentiment_score |
| 摘要 | ≤100 字一句话总结 |
| 关键要点 | 3-5 个 bullet 要点 |
| 操作建议 | 结构化（空仓/持仓/入场/止损/止盈） |
| 市场环境 | 大盘趋势 + 板块强弱 + 情绪 |
| 风险警告 | 至少一条风险提示 |
| 相关新闻 | Intel 搜索到的新闻（含链接） |

### 4.2 Deep 模式额外区块

| 区块 | 说明 |
|------|------|
| ⚔️ 多空辩论 | 多方论点 + 空方论点 + 裁判裁决 + 信心变化 |
| 🛡️ 风险评估 | 激进视角 + 保守视角 + 裁决 + 建议仓位 |
| 🎯 策略评估 | 各策略信号 + 置信度 + 核心观察 |
| 实时辩论过程 | DebatePanel / RiskDebatePanel（SSE 实时推送） |

### 4.3 Quick 模式特有区块

| 区块 | 说明 |
|------|------|
| 信号一览表 | technical + intel 两个 agent 信号对比 |

### 4.4 Chat（追问）模式

- 不出 dashboard，输出 Markdown 自由文本
- 保持当前行为不变（response_mode = "chat"）

---

## 五、缺失但可添加的报告信息

以下数据后端已可获取或稍加开发即可获得，但当前不在报告中展示：

| 信息 | 数据来源 | 添加难度 | 价值 |
|------|---------|---------|------|
| 资金流向（主力净流入/出） | Intel Agent `get_capital_flow` → `ctx.data["intel_opinion"]["capital_flow_signal"]` | 低（已有） | 高 |
| 板块排名 | Intel Agent `get_sector_rankings` | 低（已有） | 中 |
| 技术指标原始数据（MA/MACD/RSI/KDJ） | Technical Agent 计算结果 | 低（已在 opinion.raw_data） | 高 |
| 筹码分布 | `ctx.data["chip_distribution"]` | 中 | 中 |
| 实时报价（当前价/涨跌幅/成交量） | `ctx.data["realtime_quote"]` | 低（已有） | 高 |
| 历史对比（前次分析 vs 本次变化） | ReflectionService | 中 | 高 |
| 分析时间线/Agent 执行耗时 | `stats` 对象 | 低 | 低 |
| 消息来源可信度评分 | Intel 可扩展 | 高 | 中 |
| 同行业个股对比 | 需新增 Agent/工具 | 高 | 高 |
| K线形态识别结果 | Technical Agent 可扩展 | 中 | 高 |
| 支撑/压力位详细列表 | Technical Agent `key_levels` | 低（已有） | 高 |
| 分析师评级聚合 | 需新增数据源 | 高 | 中 |
| 情绪指标（恐贪指数） | Intel Agent 可计算 | 中 | 中 |

---

## 六、实施步骤

### Phase 1: 修复基础问题
1. **修复辩论 SSE 事件 type 缺失** — `debate.py` 和 `risk_debate.py` 的 progress_callback 添加 `"type"` 字段
2. **后端强制注入 dashboard 字段** — orchestrator `_normalize_dashboard_payload` 中：
   - 若 `ctx.get_data("research_plan")` 存在但 payload 无 `debate_summary` → 从 ctx 构建并注入
   - 若 `ctx.get_data("risk_debate_verdict")` 存在但 payload 无 `risk_assessment` → 从 ctx 构建并注入
   - 强制确保 `sentiment_score`、`key_points`、`operation_advice`、`risk_warning` 始终存在（兜底默认值）
3. **明确 chat 模式定位** — chat 模式首次也出 dashboard 还是纯文本？需确认产品逻辑

### Phase 2: 统一报告模板
4. **DecisionAgent prompt 重构** — 将 "include when data available" 改为明确的必填/选填规范
5. **前端 DashboardResult 增加缺失区块**：
   - 资金流向指示器
   - 实时报价信息栏
   - 支撑/压力位可视化
   - Agent 信号对比表（Technical vs Intel）
6. **空状态 UI 处理** — 每个区块在数据缺失时显示 "暂无数据" 而非完全隐藏

### Phase 3: 增强信息
7. 添加技术指标原始数据展示
8. 添加历史分析对比（与前次结论变化）
9. 添加资金流向可视化
10. 完善 K线形态识别展示

---

## 七、验收标准

- [ ] Deep 模式报告**始终**包含：辩论摘要 + 风险评估 + 策略评估 + 基础区块
- [ ] Quick 模式报告**始终**包含：基础区块 + 信号对比
- [ ] Chat 追问模式输出 Markdown 自由文本
- [ ] 同一模式下多次分析，报告结构一致（字段全覆盖，仅内容不同）
- [ ] 实时辩论 DebatePanel 在 deep 模式下正确显示多轮过程
- [ ] PDF 导出包含所有可见区块

---

> 本计划由 Copilot 2026-05-27 生成，待用户审核后开始实施。