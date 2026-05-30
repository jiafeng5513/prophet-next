
---

# 06 — 分析报告内容规范化计划（P4）

## 背景与问题

当前两种分析模式（快速 quick / 深度 deep）的分析报告内容不一致：
- 某些字段依赖 LLM 自觉输出，不保证每次都包含
- 多空辩论 / 风险辩论仅 deep 模式触发，但前端无 graceful 降级
- SSE 实时辩论事件存在 type 字段缺失 bug，前端无法正确接收
- 后端 `_normalize_dashboard_payload` 未强制填充所有 dashboard 字段

> **决策**: 移除 chat 分析模式（与 quick 完全重复），仅保留 quick / deep 两种分析模式。
> 追问（follow-up）是所有模式的通用行为，通过 `response_mode="chat"` 控制响应格式，不作为独立分析模式。

---

## 一、各模式实际运行的 Agent 链

| 项目            | quick                        | deep                       |
|-----------------|------------------------------|-----------------------------|
| Technical Agent | ✅                          | ✅                        |
| Intel Agent     | ✅                          | ✅                        |
| Risk Agent      | ❌                          | ✅                        |
| Bull/Bear 辩论  | ❌                          | ✅（需预算 >30s）          |
| Risk 辩论       | ❌                          | ✅（需预算 >30s）          |
| Skill Agent(s)  | ❌                          | ✅（路由器选择 ≤3）        |
| Decision Agent  | ✅                          | ✅                        |
| response_mode   | dashboard(首次) / chat(追问) | dashboard(首次) / chat(追问) |

> 追问（有对话历史时）自动切换 `response_mode="chat"`，返回 Markdown 自由文本，不出 dashboard。

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

### 3.3 ~~模式映射混乱~~ → 已决策：移除 chat 模式
- **决策**: 移除 chat 分析模式，仅保留 quick / deep
- **原因**: chat 模式与 quick 执行路径完全一致（`MODE_MAPPING` 映射后 fallback 到 quick），无独立存在价值
- **改动**: 从 `MODE_MAPPING` 中删除 `"chat"` 条目；前端移除"对话"模式选项；追问行为通过 `response_mode` 自动控制

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

### 4.4 追问行为（所有模式通用）

- 当存在对话历史时，自动切换 `response_mode="chat"`
- 不出 dashboard，输出 Markdown 自由文本
- 这是响应格式的切换，不是独立的分析模式

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
3. **移除 chat 分析模式** — 从 `MODE_MAPPING` 删除 `"chat"` 条目，前端移除"对话"模式选项

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
- [ ] 追问（有对话历史）时输出 Markdown 自由文本，不出 dashboard
- [ ] 前端不再暴露"对话"模式选项，仅显示"快速"和"深度"
- [ ] 同一模式下多次分析，报告结构一致（字段全覆盖，仅内容不同）
- [ ] 实时辩论 DebatePanel 在 deep 模式下正确显示多轮过程
- [ ] PDF 导出包含所有可见区块

---

> 本计划由 Copilot 2026-05-27 生成，2026-05-28 审核更新（移除 chat 模式）。


测试情况和需要改进的点：
1. 快速模式中，分析进度中的technical和intel两项在分析结束后也不打勾，只有Decision打勾
2. 在k线图标注按钮没有实际功能
3. 在侧边栏继续对话按钮目的不明，这个功能很奇怪
4. 导出pdf内容不全
5. 新建对话按钮的图标不好
6. 深度分析模式输出报告后会再次输出一次get_realtime_quote、get_daily_history、get_analysis_context等阶段
7. agent window分为左中右三栏，历史记录应该一直显示在左边，把get_realtime_quote、get_daily_history这样的过程展示放到右边，其他内容保留在中间

8. 历史记录更新不及时， 没有时间标注，点击历史记录无法会看过往的记录，无法删除历史记录
新建对话后，历史记录应该及时更新
历史记录应显示对话发生的时间
点击对应的历史记录应该显示当时的聊天内容
每条历史记录应当能独立删除，也可以一键全部清除

9. 刚打开agnent window时，历史记录显示为空，进行一次对话后，以前的历史记录会显示出来
10. 点击以前的历史记录后，仍然显示为json，即使再切换回刚刚完成的对话，仍然是显示为json

11. agnent window上方的标题“AI助手”没有意义，可以去掉， 将新建会话的按钮放到输入框的前面