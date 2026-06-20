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
