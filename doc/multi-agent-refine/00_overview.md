# 00 — 总体开发计划

## 一、核心目标

| # | 目标 | 衡量标准 |
|---|------|---------|
| 1 | **简化模式** | 用户无需理解 6 种模式的区别，只需选择分析深度 |
| 2 | **最大化数据利用** | 每一份报告都尽可能利用所有可用数据源，提高可信度 |
| 3 | **辩论成果落地** | Debate/RiskDebate 的结论必须体现在最终报告正文中 |
| 4 | **深度分析体验** | 独立页面提供更丰富的可视化和交互能力 |

## 二、现状问题总结

### 问题 1: 模式过多，用户困惑
- 6 种模式（chat/quick/standard/full/specialist/plan）对用户认知负担大
- `chat` 模式和侧边栏对话功能重复
- `quick` 和 `standard` 的区别仅在于有无 Intel 阶段，用户难以感知价值差异
- `specialist` 相比 `full` 仅多了 SkillAgent，但需要用户自行选择技能
- `plan` 模式独立于其他模式，但本质是"preview before execute"

### 问题 2: 辩论产出未进入最终报告
- `DebateCoordinator` 产出的 `research_plan` 写入 `ctx.data["research_plan"]`
- `RiskDebateCoordinator` 产出的 verdict 写入 `ctx.data["risk_debate_verdict"]`
- **但** `DecisionAgent.build_user_message()` 没有读取这些数据
- 结果: 用户看到辩论过程的动画，但最终报告没有反映辩论结论

### 问题 3: 单 Agent 架构下模式形同虚设
- `AGENT_ARCH=single` 时 AgentExecutor 走 ReAct 循环，mode 参数被忽略
- 用户选择了不同模式但获得相同结果，体验不一致

### 问题 4: 深度分析页面功能单一
- StockAnalysis.vue 是传统的"输入 → 分析 → 展示结果"
- AgentWindow.vue 更强大（有 debate/risk/progress），但是独立弹窗
- 两个页面功能重叠但能力不同

## 三、总体方案概要

### Phase 1: 模式合并（P0）
将 6 种模式合并为 3 种:
- **💬 对话** = 原 chat（纯对话，无工具调用）
- **⚡ 快速分析** = 原 quick+standard 合并（Technical + Intel → Decision）
- **🔬 深度分析** = 原 full+specialist 合并（全管线 + Debate + Risk + Skills 自动选择）
- **📋 计划模式** = 保留为深度分析的前置选项（"先看计划再执行"）

### Phase 2: 数据流优化（P1）
- DecisionAgent 接收并利用所有上游数据
- Debate/RiskDebate 结论注入 Decision 的 user message
- 技能评估结果结构化传递

### Phase 3: 深度分析页面重构（P2）
- 将 AgentWindow 的核心组件整合到 StockAnalysis 页面
- 增加多维度可视化（雷达图、时间轴、风险矩阵）
- 支持"追问"和"对比分析"

## 四、开发顺序与依赖关系

```
Phase 1 模式合并
    ├─ 1.1 后端: orchestrator 支持新模式映射
    ├─ 1.2 后端: 合并 quick/standard 逻辑
    ├─ 1.3 后端: 合并 full/specialist，自动 skill 选择
    ├─ 1.4 前端: 模式选择器 UI 简化
    └─ 1.5 plan 模式改为深度分析的选项

Phase 2 数据流优化 (依赖 Phase 1)
    ├─ 2.1 DecisionAgent 接入 debate 结论
    ├─ 2.2 DecisionAgent 接入 risk_debate 结论
    ├─ 2.3 Dashboard JSON schema 扩展（新增辩论摘要字段）
    └─ 2.4 前端 DashboardResult 组件展示新字段

Phase 3 深度分析页面 (依赖 Phase 2)
    ├─ 3.1 合并 StockAnalysis + AgentWindow 为统一体验
    ├─ 3.2 增加分析结果可视化组件
    ├─ 3.3 追问与对比功能
    └─ 3.4 历史分析回放
```

## 五、技术约束

- 不引入新依赖（不用 LangGraph / LangChain）
- 保持 `AGENT_ARCH=single` 作为降级方案
- 兼容现有 API 契约（渐进式修改，不破坏已有客户端）
- 保持 YAML 策略文件的灵活性
