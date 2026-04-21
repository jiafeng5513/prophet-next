# daily_stock_analysis 集成方案

## 1. 背景

[daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) 是一个基于 FastAPI + React 的股票分析 Web 应用。本文档规划将其中两个核心功能集成到 prophet-next（Electron + Vue 3 桌面应用）中：

| 功能 | 来源页面 | 核心能力 |
|------|---------|---------|
| **股票分析** | HomePage | 输入股票代码 → 多维度分析（技术面/基本面/舆情/AI总结）→ 决策仪表盘 |
| **问股** | ChatPage | 自然语言对话 → AI Agent + 11种策略技能 → 流式回答 + 工具调用链 |

## 2. 两个项目的技术差异

| 维度 | prophet-next | daily_stock_analysis |
|------|-------------|---------------------|
| 前端框架 | Vue 3 + Element Plus | React 19 + Tailwind CSS |
| 后端 | 无独立后端（Electron 主进程 + Python 脚本） | FastAPI + SQLite + SQLAlchemy |
| 数据源 | Binance / OKX（加密货币） | efinance / AkShare / Tushare（A股） |
| AI 能力 | 无 | LiteLLM（Gemini/Claude/DeepSeek/OpenAI） |
| 实时通信 | WebSocket（行情推送） | SSE（任务进度/对话流式输出） |
| 运行形态 | Electron 桌面应用 | Web 应用（Python 服务 + SPA） |

## 3. 推荐方案：FastAPI 后端作为 Electron 子服务 + Vue 前端重写

### 3.1 方案选型理由

1. **后端复用价值极高**：分析流水线（pipeline）、Agent 系统、数据源适配、LLM 调用等核心逻辑全在 Python 后端，代码量大且逻辑复杂，不应重写
2. **前端必须重写**：React → Vue 无法直接复用，但页面逻辑相对简单（一个搜索+报告页、一个聊天页）
3. **prophet-next 已有 Python 进程管理能力**：当前项目已有运行 Python 脚本的机制

### 3.2 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  Electron 主进程                      │
│                                                       │
│  ┌─────────────────┐    ┌──────────────────────────┐ │
│  │  窗口/标签管理    │    │  FastAPI 子进程管理       │ │
│  │  (WebContentsView)│    │  - spawn python server   │ │
│  │                   │    │  - 健康检查              │ │
│  │                   │    │  - 生命周期管理           │ │
│  └────────┬──────────┘    └───────────┬──────────────┘ │
│           │                           │                 │
└───────────┼───────────────────────────┼─────────────────┘
            │                           │
    ┌───────▼───────┐          ┌────────▼────────┐
    │  渲染进程 (Vue) │  HTTP   │  FastAPI 服务    │
    │               │  /SSE    │  localhost:8000  │
    │  - 股票分析页  │◄────────►│                  │
    │  - 问股对话页  │          │  - 分析 pipeline │
    │  - 设置页     │          │  - Agent 系统    │
    │  - K线图页    │          │  - 数据源适配     │
    └───────────────┘          │  - LLM 调用      │
                               │  - SQLite 存储   │
                               └──────────────────┘
```

### 3.3 与现有模式框架的对接

prophet-next 已规划了四种模式，其中两种目前显示"正在开发中"，正好可以承载新功能：

| prophet-next 模式 | 当前状态 | 集成功能 |
|-------------------|---------|---------|
| `trading_mode` | 已实现（K线图表） | 不变 |
| `developing_mode` | 已实现（Monaco 编辑器） | 不变 |
| `market_analyze_mode` | 占位（正在开发中） | **股票分析功能** |
| `news_mode` | 占位（正在开发中） | **问股功能**（或改名为 `agent_mode`） |

## 4. 实施任务分解

### 阶段一：FastAPI 后端集成（P0）

#### 4.1 Python 环境管理

- 在工作区目录下创建 `venv/` 虚拟环境（或复用 conda 环境）
- 安装 `daily_stock_analysis` 的依赖（`requirements.txt`）
- 在设置页面提供 Python 环境路径配置

#### 4.2 FastAPI 子进程管理

在 Electron 主进程中实现：

```
src/main/index.js 新增：
  - startFastAPIServer()    // spawn python 子进程运行 server.py
  - stopFastAPIServer()     // 优雅关闭
  - checkServerHealth()     // 轮询 /api/v1/health 确认就绪
  - 窗口关闭时自动停止服务
```

关键配置项（存入设置 / localStorage）：
- `fastapi-port`：服务端口，默认 8000
- `python-path`：Python 解释器路径
- `dsa-path`：daily_stock_analysis 项目路径

#### 4.3 配置管理

在设置页面新增配置区域：

| 配置项 | 类型 | 说明 |
|--------|------|------|
| LLM Provider | 下拉选择 | Gemini / Claude / DeepSeek / OpenAI |
| LLM API Key | 密码输入 | 对应 provider 的 API Key |
| LLM Model | 文本输入 | 模型名称（如 gemini-2.0-flash） |
| 搜索引擎 API Key | 密码输入 | Tavily / SerpAPI（用于舆情分析，可选） |
| FastAPI 端口 | 数字输入 | 默认 8000 |
| DSA 项目路径 | 目录选择 | daily_stock_analysis 所在路径 |

这些配置将被写入 `.env` 文件供 FastAPI 读取。

### 阶段二：股票分析页面（P1）

#### 4.4 新增文件

```
src/renderer/
  stock-analysis.html              # 入口 HTML
  src/
    stock-analysis.js              # Vue 挂载入口
    StockAnalysis.vue              # 主页面组件
    components/
      StockSearchInput.vue         # 股票搜索自动补全
      AnalysisTaskPanel.vue        # 任务进度面板（SSE）
      AnalysisReport.vue           # Markdown 报告渲染
      AnalysisHistory.vue          # 历史记录侧栏
```

#### 4.5 调用的后端 API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/stocks/search?q=` | 股票搜索自动补全 |
| POST | `/api/v1/analysis/analyze` | 触发分析（异步） |
| GET | `/api/v1/analysis/status/{task_id}` | 查询任务状态 |
| SSE | `/api/v1/analysis/tasks/stream` | 实时任务进度推送 |
| GET | `/api/v1/analysis/tasks` | 历史任务列表 |

#### 4.6 核心交互流程

```
用户输入股票代码/名称
    → 自动补全（GET /stocks/search）
    → 点击"分析"
    → POST /analysis/analyze（返回 task_id）
    → SSE 监听任务进度
    → 进度面板实时更新（已启动 → 获取数据 → 技术分析 → AI 生成报告）
    → 分析完成 → 渲染 Markdown 报告（决策仪表盘）
    → 可点击"追问 AI"跳转到问股页面
```

### 阶段三：问股对话页面（P1）

#### 4.7 新增文件

```
src/renderer/
  stock-chat.html                  # 入口 HTML
  src/
    stock-chat.js                  # Vue 挂载入口
    StockChat.vue                  # 主页面组件
    components/
      ChatMessageList.vue          # 消息列表（支持 Markdown 渲染）
      ChatInput.vue                # 输入框 + 发送按钮
      SkillSelector.vue            # 策略技能选择器
      ThinkingSteps.vue            # 思考过程/工具调用展示
      ChatSessionList.vue          # 会话列表侧栏
```

#### 4.8 调用的后端 API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/agent/skills` | 获取可用策略列表 |
| POST | `/api/v1/agent/chat/stream` | 流式对话（SSE） |
| GET | `/api/v1/agent/chat/sessions` | 会话列表 |
| GET | `/api/v1/agent/chat/sessions/{id}` | 获取会话消息 |
| DELETE | `/api/v1/agent/chat/sessions/{id}` | 删除会话 |

#### 4.9 内置策略技能（11种）

| 技能 ID | 名称 | 说明 |
|---------|------|------|
| `bull_trend` | 多头趋势 | MA 多头排列 + 低乖离率 |
| `ma_golden_cross` | 均线金叉 | MA5 上穿 MA10/MA20 |
| `volume_breakout` | 放量突破 | 突破近期高点 + 量能放大 |
| `shrink_pullback` | 缩量回踩 | 回踩均线 + 量能萎缩 |
| `bottom_volume` | 底部放量 | 底部反转信号 |
| `dragon_head` | 龙头策略 | 强势龙头追涨 |
| `one_yang_three_yin` | 一阳夹三阴 | 主力洗盘反包 |
| `box_oscillation` | 箱体震荡 | 区间高抛低吸 |
| `chan_theory` | 缠论 | 笔/线段/中枢分析 |
| `wave_theory` | 波浪理论 | 艾略特波浪计数 |
| `emotion_cycle` | 情绪周期 | 市场情绪轮动 |

#### 4.10 核心交互流程

```
用户输入自然语言问题（如"用缠论分析贵州茅台"）
    → 可选：选择策略技能标签
    → 点击发送
    → POST /agent/chat/stream（SSE 流式响应）
    → 实时显示：
        - 思考步骤（"正在获取行情数据..."）
        - 工具调用（"调用 analyze_trend..."）
        - 最终回答（Markdown 渲染）
    → 支持追问（多轮对话，session_id 保持上下文）
```

### 阶段四：跨模式联动（P2）

#### 4.11 K线图 → 分析联动

- 在交易模式的 K 线图页面添加"AI 分析"按钮
- 点击后切换到 `market_analyze_mode`，自动填充当前股票代码触发分析

#### 4.12 分析报告 → 问股联动

- 分析报告底部添加"追问 AI"按钮
- 点击后切换到问股页面，携带股票代码和分析上下文

#### 4.13 分析报告嵌入 K 线图预览

- 在报告的关键点位（买入/止损/目标价）处嵌入小型 K 线图
- 复用 TradingView Lightweight Charts

## 5. 关键依赖与前置条件

### 5.1 Python 依赖

`daily_stock_analysis` 核心依赖：
- `fastapi` + `uvicorn`：Web 框架
- `litellm`：统一 LLM 调用
- `efinance` / `akshare`：A 股数据源
- `sqlalchemy`：数据库 ORM
- `tavily-python` / `serpapi`：新闻搜索（可选）

### 5.2 必要条件

1. **LLM API Key**：两个功能的核心都依赖 LLM，用户必须配置至少一个 API Key
2. **Python 环境**：需要 Python 3.10+，建议使用 conda/venv 隔离
3. **网络环境**：A 股数据源（efinance/AkShare）需要中国大陆网络；LLM API 可能需要代理

### 5.3 Vue 前端新增依赖

| 包 | 用途 |
|----|------|
| `markdown-it` | Markdown 渲染（分析报告 + 对话消息） |
| `highlight.js` | 代码高亮（报告中的代码块） |

## 6. 备选方案：WebView 嵌入（快速验证）

如果想快速看到效果，可以临时采用：

1. 将 `daily_stock_analysis` 的 React 前端构建为静态文件
2. FastAPI 同时托管静态文件，在 `http://localhost:8000` 提供完整 Web UI
3. 在 Electron 中用 `WebContentsView` 直接加载该地址

**优点**：零前端开发，功能完整  
**缺点**：UI 风格不统一、无法与 prophet-next 深度联动、两套 UI 体系

此方案仅建议用于早期验证后端可用性，不作为最终方案。

## 7. 任务优先级总览

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | Python 环境管理（venv 配置） | 无 |
| P0 | Electron 管理 FastAPI 子进程（启动/停止/健康检查） | Python 环境 |
| P0 | 设置页面增加 LLM / API 配置项 | 无 |
| P1 | 股票分析 Vue 页面（搜索 + 报告 + 进度 + 历史） | FastAPI 服务 |
| P1 | 问股对话 Vue 页面（聊天 + 策略选择 + 流式输出） | FastAPI 服务 |
| P2 | K 线图 → 分析 跨模式联动 | 股票分析页 |
| P2 | 分析 → 问股 跨页面联动 | 两个页面都完成 |
| P2 | 报告中嵌入 K 线图预览 | 股票分析页 |
