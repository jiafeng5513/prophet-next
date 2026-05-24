# Multi-Agent 细化优化开发计划

> 本文件夹包含对 prophet-next 多 Agent 系统的细化与优化开发计划。
> 基于已有 `doc/multi-agent-plan/` 中的升级计划,进一步聚焦于:
> 1. 模式合并简化 — 将 6 种模式精简为易于理解的 3 种
> 2. 数据利用最大化 — 让报告充分利用所有可用数据源
> 3. 深度分析页面重构 — 独立页面的 UX 增强

## 文件索引

| 文件 | 内容 |
|------|------|
| [00_overview.md](./00_overview.md) | 总体开发计划与目标 |
| [01_current_modes_analysis.md](./01_current_modes_analysis.md) | 现有 6 种模式的详细工作流与问题分析 |
| [02_mode_consolidation.md](./02_mode_consolidation.md) | 模式合并方案（6→3）|
| [03_data_utilization.md](./03_data_utilization.md) | 数据源最大化利用方案 |
| [04_deep_analysis_page.md](./04_deep_analysis_page.md) | 深度分析页面增强计划 |

## 开发优先级与进度

| 优先级 | 阶段 | 状态 | 完成日期 |
|--------|------|------|----------|
| **P0** | Phase 1 — 模式合并（6→3+1） | ✅ 已完成 | 2026-05-24 |
| **P1** | Phase 2 — 数据流优化 | ✅ 已完成 | 2026-05-24 |
| **P2** | Phase 3 — 深度分析页面重构 | ✅ 已完成 | 2026-05-24 |

## 完成总结

所有三个阶段均已实施并通过验证。核心成果:

- **模式简化**: 6 种模式 → `chat` / `quick` / `deep` / `plan`，向后兼容旧模式名
- **数据流贯通**: DecisionAgent 完整接收 debate/risk/skill/market 数据，权重化综合决策
- **统一分析页面**: StockAnalysis 三栏布局（历史 + 结果 + 实时进度），集成流式分析、雷达图、追问、导出
- **AgentWindow 轻量化**: 转型为浮动对话助手，不再承担主分析入口职责
