# 02 — 模式合并方案（6 → 3+1）

> **状态: ✅ 已完成 (2026-05-24)**
>
> 已实施内容:
> - `orchestrator.py`: VALID_MODES=("quick","deep"), MODE_MAPPING 兼容旧名
> - `config.py`: 默认 mode "quick", __post_init__ 映射遗留值
> - `factory.py`: 默认 mode "quick"
> - `plan_mode.py`: 推荐 deep
> - `api/v1/endpoints/agent.py`: 入口处映射
> - 前端: ChatInput/AgentWindow/AgentProgress/Settings 全部更新为 quick/deep

## 一、设计原则

1. **用户视角优先**: 用户只需关心"我要多详细的分析"，不需要理解 Agent 架构
2. **渐进增强**: 低级模式是高级模式的子集，不存在能力倒退
3. **自动化优于配置**: SkillRouter 自动选择技能，用户可选但不必选
4. **向后兼容**: API 层保留旧 mode 值映射到新模式

---

## 二、新模式定义

### 模式 1: 💬 对话 (chat)

**用途**: 纯粹的 AI 对话，无数据工具调用

**映射**: 保持不变

**行为**:
- 不调用任何工具
- LLM 直接回答
- 适用于: 概念解释、策略讨论、市场教育

**UI 位置**: 侧边栏 ChatPanel 默认模式

---

### 模式 2: ⚡ 快速分析 (quick)

**用途**: 一键生成完整分析报告

**映射**: 合并原 `quick` + `standard`

**Agent 链** (multi arch):
```
[TechnicalAgent ∥ IntelAgent] → DecisionAgent
```

**变更**:
- 原 `quick` 模式（无 Intel）被移除 — 情报搜索不应该是可选的
- IntelAgent 始终参与，确保报告有新闻/情报维度
- 并行执行 Technical + Intel，延迟不增加

**工具全集**:
- 实时行情 + 历史K线 + 技术指标 + 筹码分布
- 新闻搜索 + 综合情报 + 资金流 + 基本面
- **新增**: get_market_indices（大盘参考）
- **新增**: get_sector_rankings（板块强弱）

**输出**: 完整 Dashboard JSON

**适用场景**:
- 快速了解个股当前状态
- 日常盘中快速评估
- 大多数用户的默认选择

---

### 模式 3: 🔬 深度分析 (deep)

**用途**: 全面深度分析，含多角度辩论和策略评估

**映射**: 合并原 `full` + `specialist`

**Agent 链** (multi arch):
```
[TechnicalAgent ∥ IntelAgent] → RiskAgent
→ [Bull/Bear Debate]
→ [Risk Debate (3视角)]
→ [SkillAgent ×1-3 (自动选择)]
→ DecisionAgent
```

**核心变更**:
1. Skills **始终自动选择** — SkillRouter 根据市场状态自动匹配
2. 用户仍可通过 UI 手动指定技能（覆盖自动选择）
3. Debate + RiskDebate 结论**必须**注入 DecisionAgent
4. Plan 模式改为深度分析的前置选项（勾选"先看计划"）

**工具全集**: 快速分析的全部 + RiskAgent 工具 + 回测工具

**输出**: 完整 Dashboard JSON + 辩论摘要 + 风险评估 + 技能意见

**适用场景**:
- 重大投资决策前的全面评估
- 陌生标的的首次研究
- 需要多角度验证的场景

---

### 选项: 📋 计划预览 (plan)

**不再是独立模式**，而是深度分析的前置选项:

```
[ ] 执行前先预览分析计划
```

勾选后:
1. LLM 先生成分析计划 → 展示给用户
2. 用户确认 → 以深度分析模式执行
3. 用户可修改计划中的技能选择

---

## 三、向后兼容映射

```python
MODE_MAPPING = {
    # 新模式
    "chat": "chat",
    "quick": "quick",     # 新 quick = 旧 standard
    "deep": "deep",       # 新 deep = 旧 full + specialist

    # 旧模式兼容（已废弃但不报错）
    "standard": "quick",  # 映射到新 quick
    "full": "deep",       # 映射到新 deep
    "specialist": "deep", # 映射到新 deep
    "plan": "deep",       # plan 不再是独立 mode
}
```

API 请求中的旧 mode 值自动映射，不破坏现有客户端。

---

## 四、实现步骤

### 4.1 后端改造

```
backend/src/agent/orchestrator.py:
  - VALID_MODES = ("quick", "deep")  # 移除 standard/full/specialist
  - _build_agent_chain():
      quick → [Technical ∥ Intel] → Decision
      deep  → [Technical ∥ Intel] → Risk → Debate → RiskDebate → Skills → Decision

backend/src/agent/factory.py:
  - build_agent_executor() 中添加 MODE_MAPPING 兼容层

backend/api/v1/endpoints/agent.py:
  - stream endpoint: mode 参数经过 MODE_MAPPING 转换
  - plan 逻辑改为: if request.plan_preview → PlanModeHandler + 后续执行
```

### 4.2 前端改造

```
src/renderer/src/AgentWindow.vue:
  - allowedModes = ["chat", "quick", "deep"]
  - modeLabels = { chat: "💬 对话", quick: "⚡ 快速分析", deep: "🔬 深度分析" }
  - 新增 checkbox: "执行前预览计划"（仅 deep 模式可见）
  - 移除 skills 手动选择 UI（改为高级选项，默认折叠）

src/renderer/src/components/sidebar/ChatPanel.vue:
  - 模式选择简化为同样的 3 个选项
```

### 4.3 单 Agent 架构适配

```
backend/src/agent/executor.py:
  - mode="chat" → response_mode="chat"
  - mode="quick" → 标准 ReAct，工具集 = Technical + Intel tools
  - mode="deep" → 标准 ReAct，工具集 = 全量
  - 差异仅体现在工具集范围和系统 prompt 深度要求
```

---

## 五、风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| 用户已习惯旧模式 | 低 — 大部分用户使用 standard/full | 渐进迁移 + 兼容映射 |
| specialist 高级用户不满 | 中 — 自动技能选择可能不如手选精准 | 保留手动技能选择作为高级选项 |
| plan 模式用户习惯被打破 | 低 — plan 使用率很低 | 改为 checkbox，功能不变 |
| API 兼容性 | 低 — 有 MODE_MAPPING | 旧值继续工作，仅日志 warning |
