# UI 一致性重构开发计划

> **目标**: 所有模式/视图统一为「左侧面板 + 主视图」两栏布局，消除贯穿页面的全宽标题栏，营造与 Visual Studio / VS Code 一致的视觉体验。

---

## 一、现状分析

### 1.1 整体架构

应用采用 Electron + Vue 3，主窗口由以下区域组成：

```
┌──────────────────────────────────────────────────────────┐
│  Title Bar (30px)                                        │
├────┬──────────┬──────────────────────┬──────────────────┤
│    │          │  Tab Bar (36px)      │                  │
│ A  │          ├──────────────────────┤                  │
│ c  │          │                      │                  │
│ t  │  Left    │   Main Content       │   Agent Panel    │
│ i  │  Panel   │   (WebContentsView)  │   (350px,       │
│ v  │  (可选)  │                      │    可折叠)       │
│ i  │          │                      │                  │
│ t  │          │                      │                  │
│ y  │          │                      │                  │
│    │          │                      │                  │
│ Bar├──────────┴──────────────────────┴──────────────────┤
│48px│  Status Bar (22px)                                  │
└────┴─────────────────────────────────────────────────────┘
```

- **Activity Bar** (48px): 左侧模式切换图标栏（交易/开发/新闻/市场分析/持仓/回测/设置）
- **Tab Bar** (36px): 多标签页（仅交易和开发模式）
- **Left Panel**: 目前仅开发模式有 Explorer (250px)
- **Main Content**: WebContentsView，每个标签页独立
- **Agent Panel**: 右侧 AI 助手面板 (350px，可折叠)

### 1.2 各视图当前布局状态

| 视图 | 布局模式 | 全宽标题 | 左侧面板 | 问题 |
|------|----------|----------|----------|------|
| **交易模式** (Chart.vue) | 全屏图表 | ❌ | ❌ | 无左侧标的浏览器 |
| **开发模式** (Editor.vue) | 全屏编辑器 | ❌ | ✅ (Explorer) | ✅ 已符合目标 |
| **新闻** (News.vue) | 左右分栏 | ⚠️ 顶部过滤栏 | ✅ (时间线 340px) | 顶部 NewsFilter 贯穿全宽 |
| **市场分析** (StockAnalysis.vue) | 左右分栏 | ⚠️ 顶部搜索栏 | ✅ (历史面板，可折叠) | 顶部搜索栏贯穿全宽 |
| **持仓管理** (Portfolio.vue) | 标题+内容 | ⚠️ 顶部 tab 导航 | ❌ | 无左侧面板，分类在顶部 tab |
| **回测分析** (Backtest.vue) | 标题+内容 | ⚠️ 顶部 tab 导航 | ❌ | 无左侧面板，分类在顶部 tab |
| **设置** (Settings.vue) | 标题+左右分栏 | ⚠️ 顶部标题栏 | ✅ (导航 250px) | 顶部 header 贯穿全宽 |

---

## 二、目标布局

所有模式统一为以下布局（页面内部不再有全宽标题栏）：

```
┌──────────────────────────────────────────┐
│ ┌────────────┐ ┌──────────────────────┐  │
│ │            │ │                      │  │
│ │  左侧面板  │ │     主视图           │  │
│ │  (固定宽度) │ │     (flex: 1)       │  │
│ │            │ │                      │  │
│ │            │ │                      │  │
│ │            │ │                      │  │
│ └────────────┘ └──────────────────────┘  │
└──────────────────────────────────────────┘
```

各模式具体内容：

| 模式 | 左侧面板内容 | 主视图内容 |
|------|-------------|-----------|
| 交易 | 标的浏览器 (SymbolBrowser) | 多标签页 K 线图 |
| 开发 | 文件资源管理器 (Explorer) | Monaco 编辑器 |
| 新闻 | 时间线 (Timeline) + 过滤器 | 新闻详情 |
| 市场分析 | 分析历史列表 | 搜索栏 + 分析报告 |
| 持仓管理 | 分类导航（总览/交易/现金流/公司行动/账户/导入/风险） | 对应分类内容 |
| 回测分析 | 分类导航（运行/结果/业绩/个股表现） | 对应分类内容 |
| 设置 | 分类导航 | 设置表单 |

---

## 三、通用左侧面板规范

为保证视觉一致性，所有左侧面板遵循相同的设计规范：

### 3.1 尺寸与样式

```css
.side-panel {
  width: 260px;            /* 统一默认宽度 */
  min-width: 200px;
  max-width: 400px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #252526;     /* VS Code 侧栏背景色 */
  border-right: 1px solid #333;
  overflow: hidden;
  flex-shrink: 0;
}
```

### 3.2 面板标题栏

```css
.side-panel-header {
  height: 35px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #bbbbbb;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}
```

### 3.3 面板内容

```css
.side-panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
```

### 3.4 页面根容器

```css
.view-container {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #1e1e1e;
}

.main-view {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
```

---

## 四、实施方案（按视图）

### Phase 0: 提取公共样式组件

**文件变更**:
- 新建 `src/renderer/src/styles/layout.css` — 公共两栏布局样式

**工作内容**:
1. 将 3.1 ~ 3.4 中定义的通用样式抽取为公共 CSS
2. 定义 CSS 变量用于左侧面板宽度、颜色等可配置项
3. 各页面 import 此公共样式

**预计改动量**: 小

---

### Phase 1: 交易模式 — 添加标的浏览器左侧面板

**当前状态**: Chart.vue 全屏显示 K 线图，SymbolBrowser.vue 作为独立页面存在

**目标**:
```
┌────────────────┬──────────────────────────┐
│  标的浏览器     │                          │
│  ┌────────────┐│      K 线图表             │
│  │ 市场类型    ││   (TVChartContainer)     │
│  │ 搜索栏     ││                          │
│  ├────────────┤│                          │
│  │            ││                          │
│  │ 标的列表   ││                          │
│  │ (可滚动)   ││                          │
│  │            ││                          │
│  ├────────────┤│                          │
│  │ 状态栏     ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**方案**: 利用主进程已有的左面板机制 (explorerPanel)，将其泛化为通用左面板

**文件变更**:
- `src/main/index.js`:
  - 将 `explorerPanelVisible` 泛化为 `leftPanelVisible`，根据当前 mode 决定左面板内容
  - 交易模式下左面板加载 `symbol-browser.html`
  - 添加 `left-panel-config` IPC，支持各模式配置左面板 URL 和宽度
- `src/renderer/src/index.js`:
  - 模式切换时通知主进程更新左面板
  - 交易模式显示左面板，非多标签模式的左面板由各页面内部管理
- `src/renderer/src/SymbolBrowser.vue`:
  - 添加与主视图的通信：选中标的时通过 IPC 通知打开/切换到对应 chart tab
  - 移除独立页面的多余样式，适配作为左面板使用
- `src/renderer/symbol-browser.html`:
  - 可能需要调整以适配面板模式

**实现要点**:
1. SymbolBrowser 中双击标的 → IPC `open-chart-tab` → 主进程创建新 chart tab 或激活已有
2. SymbolBrowser 右键菜单保留"打开图表"功能
3. 支持拖拽标的到图表区域切换品种
4. 左面板可折叠/展开

**预计改动量**: 大（涉及主进程逻辑改造）

---

### Phase 2: 新闻页 — 移除顶部过滤栏

**当前状态**: 顶部 NewsFilter（全宽）+ 左侧 Timeline (340px) + 右侧详情

**目标**:
```
┌────────────────┬──────────────────────────┐
│  新闻时间线     │                          │
│  ┌────────────┐│      新闻详情             │
│  │ 过滤器     ││   (NewsDetail)           │
│  │ (折叠/展开) ││                          │
│  ├────────────┤│                          │
│  │            ││                          │
│  │  新闻列表  ││                          │
│  │  (时间分组) ││                          │
│  │            ││                          │
│  │            ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**文件变更**:
- `src/renderer/src/News.vue`:
  - 移除 `<div class="news-page">` 外层 column 布局
  - 改为纯 `flex-direction: row` 两栏布局
  - 将 NewsFilter 嵌入左侧面板顶部（可折叠区域）
  - 左侧面板宽度从 340px 调整为 260px
  - 应用公共 `.view-container` / `.side-panel` / `.main-view` 样式
- `src/renderer/src/components/news/NewsFilter.vue`:
  - 调整为纵向排列，适配窄面板宽度
  - 添加折叠/展开功能（点击标题折叠过滤器区域）
- `src/renderer/src/components/news/NewsTimeline.vue`:
  - 宽度改为 100%，填满左侧面板

**预计改动量**: 中

---

### Phase 3: 市场分析 — 移除顶部搜索栏

**当前状态**: 可折叠历史面板 + 全宽搜索栏 + 主内容区

**目标**:
```
┌────────────────┬──────────────────────────┐
│  分析历史       │  ┌──────────────────┐    │
│  ┌────────────┐│  │ 搜索栏 (内嵌)     │    │
│  │            ││  └──────────────────┘    │
│  │ 历史记录   ││                          │
│  │ 列表       ││  分析报告内容             │
│  │ (可滚动)   ││  (可滚动)                │
│  │            ││                          │
│  │            ││                          │
│  │            ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**文件变更**:
- `src/renderer/src/StockAnalysis.vue`:
  - 移除 `.stock-analysis-page` 外层 column 布局
  - 将历史面板从 `v-show` 切换改为始终显示的左侧面板
  - 移除全宽搜索栏 `.search-bar`，将搜索组件嵌入主视图顶部（仅占主视图宽度）
  - 应用公共 `.view-container` / `.side-panel` / `.main-view` 样式
  - 移除历史面板的折叠/展开按钮（面板始终可见）

**预计改动量**: 中

---

### Phase 4: 持仓管理 — 标签页导航移入左侧面板

**当前状态**: 全宽 `.top-bar`（标题 + 水平 tab 导航 + 账户选择器）+ 主内容区

**目标**:
```
┌────────────────┬──────────────────────────┐
│  持仓管理       │                          │
│  ┌────────────┐│     当前分类内容           │
│  │ 账户选择器  ││  (总览/交易/现金流/...)   │
│  ├────────────┤│                          │
│  │ ● 总览     ││                          │
│  │   交易记录  ││                          │
│  │   现金流    ││                          │
│  │   公司行动  ││                          │
│  │   账户管理  ││                          │
│  │   CSV导入   ││                          │
│  │   风险分析  ││                          │
│  ├────────────┤│                          │
│  │ 服务状态   ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**文件变更**:
- `src/renderer/src/Portfolio.vue`:
  - 移除 `.top-bar` 全宽标题栏
  - 新增左侧面板：
    - 顶部面板标题 "持仓管理"
    - 账户选择器下拉框
    - 纵向分类导航列表（替代水平 tab）
    - 底部服务状态指示器
  - 分类导航项使用 VS Code 树视图风格：
    - 图标 + 文字
    - hover 高亮 (#2a2d2e)
    - 选中态左侧边框 (#0078d4)
  - 主视图区域保持现有 tab-content 渲染逻辑不变
  - 应用公共 `.view-container` / `.side-panel` / `.main-view` 样式

**预计改动量**: 中

---

### Phase 5: 回测分析 — 标签页导航移入左侧面板

**当前状态**: 全宽 `.top-bar`（标题 + 水平 tab 导航）+ 主内容区（与 Portfolio 结构相同）

**目标**:
```
┌────────────────┬──────────────────────────┐
│  回测分析       │                          │
│  ┌────────────┐│     当前分类内容           │
│  │ ● 运行回测  ││  (表单/结果/图表/...)     │
│  │   回测结果  ││                          │
│  │   业绩总览  ││                          │
│  │   个股表现  ││                          │
│  ├────────────┤│                          │
│  │ 服务状态   ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**文件变更**:
- `src/renderer/src/Backtest.vue`:
  - 移除 `.top-bar` 全宽标题栏
  - 新增左侧面板：
    - 顶部面板标题 "回测分析"
    - 纵向分类导航列表（运行回测/回测结果/业绩总览/个股表现）
    - 底部服务状态指示器
  - 导航项样式同 Portfolio（VS Code 树视图风格）
  - 主视图区域保持现有 tab-content 渲染逻辑不变
  - 应用公共 `.view-container` / `.side-panel` / `.main-view` 样式

**预计改动量**: 中

---

### Phase 6: 设置页 — 移除顶部标题栏

**当前状态**: 全宽 `.settings-header`（标题 + 导入/导出/保存按钮）+ 左侧导航 (250px) + 右侧内容

**目标**:
```
┌────────────────┬──────────────────────────┐
│  设置           │                          │
│  ┌────────────┐│     设置表单内容           │
│  │ 本地配置    ││                          │
│  │ DSA后端     ││                          │
│  │ LLM 通道   ││                          │
│  │ 运行参数    ││                          │
│  ├────────────┤│                          │
│  │            ││                          │
│  │ [导入]     ││                          │
│  │ [导出]     ││                          │
│  │ [保存]     ││                          │
│  └────────────┘│                          │
└────────────────┴──────────────────────────┘
```

**文件变更**:
- `src/renderer/src/Settings.vue`:
  - 移除 `.settings-header` 全宽标题栏
  - 将标题移入左侧面板顶部 `.side-panel-header`
  - 将操作按钮（导入/导出/保存）移入左侧面板底部
  - 左侧面板宽度从 250px 调整为 260px（统一）
  - 应用公共 `.view-container` / `.side-panel` / `.main-view` 样式

**预计改动量**: 小

---

## 五、实施顺序与依赖关系

```
Phase 0: 公共样式组件     ← 无依赖，最先实施
    │
    ├─→ Phase 6: 设置页 (最小改动，用于验证公共样式)
    │
    ├─→ Phase 2: 新闻页
    │
    ├─→ Phase 3: 市场分析
    │
    ├─→ Phase 4: 持仓管理
    │
    ├─→ Phase 5: 回测分析
    │
    └─→ Phase 1: 交易模式  ← 改动最大，最后实施
```

**推荐实施顺序**: Phase 0 → 6 → 2 → 3 → 4 → 5 → 1

**理由**:
1. Phase 0 提取公共样式，为后续所有 Phase 提供基础
2. Phase 6 (设置页) 改动最小，适合首先验证公共样式方案
3. Phase 2/3 (新闻/市场分析) 已有左侧面板，只需移除全宽标题
4. Phase 4/5 (持仓/回测) 结构相似，可并行或顺序开发
5. Phase 1 (交易模式) 涉及主进程改造和跨视图通信，复杂度最高

---

## 六、注意事项

### 6.1 架构约束
- 交易模式和开发模式使用 **多标签页 + WebContentsView**，左面板需由主进程管理布局边界
- 其他模式（新闻/分析/持仓/回测/设置）为 **单页面**，左面板在页面 Vue 组件内部实现即可
- Agent Panel (右侧) 的折叠/展开不受影响

### 6.2 样式一致性检查清单
- [ ] 所有左侧面板背景色统一为 `#252526`
- [ ] 所有左侧面板宽度默认 260px
- [ ] 所有面板标题栏高度 35px，字体 11px 大写
- [ ] 所有面板边框颜色 `#333`
- [ ] 导航项 hover 色 `#2a2d2e`，选中态 `#37373d` + 左边框 `#0078d4`
- [ ] 无任何贯穿全宽的标题/搜索/过滤栏
- [ ] 主视图区域统一 `flex: 1; overflow: hidden`

### 6.3 兼容性
- 浏览器调试模式 (`npm run dev:browser`) 需同步适配
- 左面板折叠/展开状态应持久化到 localStorage
- 窗口 resize 时布局自适应

---

## 七、底部终端面板（Terminal Panel）

> **目标**: 模仿 VS Code 底部终端面板，支持查看后端服务日志和运行系统命令（包括进入 uv 管理的 Python 环境）。

### 7.1 功能概述

```
┌─────────────────────────────────────────────────────────────┐
│  Activity Bar │ Left Panel │ Main Content       │Agent Panel │
│               │            │                    │            │
│               │            │                    │            │
│               │            │                    │            │
│               ├────────────┴────────────────────┤            │
│               │ [终端面板 - 可上下拖拽调整高度]    │            │
│               │ ┌─────────────────────────────┐ │            │
│               │ │ [后端日志] [终端]  [+]  [×]  │ │            │
│               │ ├─────────────────────────────┤ │            │
│               │ │                             │ │            │
│               │ │   xterm.js 终端内容          │ │            │
│               │ │                             │ │            │
│               │ └─────────────────────────────┘ │            │
├───────────────┴─────────────────────────────────┴────────────┤
│  Status Bar                                                   │
└───────────────────────────────────────────────────────────────┘
```

**功能列表**:

| 功能 | 说明 |
|------|------|
| **后端日志** | 实时显示 DSA 后端服务 (uvicorn) 的 stdout/stderr 日志，只读 |
| **系统终端** | 可交互的 shell 终端 (Windows: PowerShell, macOS/Linux: bash/zsh) |
| **UV 环境** | 终端自动进入 `backend/` 目录并激活 uv 管理的 Python 虚拟环境 |
| **多标签** | 支持多个终端实例，标签页切换 |
| **面板折叠** | 可通过状态栏按钮或快捷键折叠/展开终端面板 |
| **高度调整** | 面板顶部有拖拽手柄，可上下拖拽调整高度 |

### 7.2 技术方案

#### 核心依赖

| 库 | 用途 | 版本 |
|----|------|------|
| `@xterm/xterm` | 终端 UI 渲染 (xterm.js v5) | ^5.x |
| `@xterm/addon-fit` | 自适应容器尺寸 | ^0.10.x |
| `@xterm/addon-web-links` | 可点击链接 | ^0.11.x |
| `node-pty` | 主进程伪终端 (PTY) | ^1.x |

#### 架构设计

```
┌─ 渲染进程 ─────────────────────────┐    ┌─ 主进程 ────────────────────┐
│                                     │    │                             │
│  TerminalPanel.vue                  │    │  terminal-manager.js        │
│  ├─ 标签栏 (后端日志 / 终端 / ...)   │    │  ├─ ptyProcesses: Map       │
│  ├─ xterm.js Terminal 实例          │◄──IPC──┤  ├─ logStream (只读)      │
│  └─ resize / 输入 → IPC 发送        │    │  └─ 管理 pty 生命周期        │
│                                     │    │                             │
└─────────────────────────────────────┘    └─────────────────────────────┘
```

**数据流 — 后端日志**:
1. 主进程 `spawn` 启动 DSA 服务时，将 stdout/stderr 数据 **缓存到 ring buffer**
2. 渲染进程打开"后端日志"标签时，通过 IPC 请求历史日志 + 订阅新日志
3. 主进程通过 `mainWindow.webContents.send('terminal-data', { id, data })` 推送
4. 渲染进程 xterm 实例 `write(data)` 渲染

**数据流 — 交互终端**:
1. 渲染进程请求创建新终端: `ipcRenderer.invoke('terminal-create', { cwd, env })`
2. 主进程通过 `node-pty` 创建 PTY 进程，返回终端 ID
3. 用户输入: 渲染进程 `ipcRenderer.send('terminal-input', { id, data })`
4. PTY 输出: 主进程 `mainWindow.webContents.send('terminal-data', { id, data })`
5. 窗口 resize: 渲染进程 `ipcRenderer.send('terminal-resize', { id, cols, rows })`

### 7.3 布局定位

终端面板位于 **主内容区域底部**，与 Activity Bar 和 Status Bar 平行，不覆盖 Left Panel：

```
x: ACTIVITY_BAR_WIDTH + leftPanelWidth
y: windowHeight - STATUS_BAR_HEIGHT - terminalPanelHeight
width: mainContentWidth (含 Agent Panel 宽度内)
height: terminalPanelHeight (默认 250px, 可拖拽调整)
```

**关键布局参数**:
```javascript
const TERMINAL_PANEL_MIN_HEIGHT = 100    // 最小高度
const TERMINAL_PANEL_MAX_RATIO = 0.7     // 最大占主内容区 70%
const TERMINAL_PANEL_DEFAULT_HEIGHT = 250 // 默认高度
const TERMINAL_PANEL_HEADER_HEIGHT = 36   // 终端标签栏高度
```

### 7.4 实施阶段

#### Phase 7A: 基础设施 — 安装依赖 & 主进程 PTY 管理

**工作内容**:
1. 安装 `@xterm/xterm`, `@xterm/addon-fit`, `@xterm/addon-web-links`, `node-pty`
2. 配置 `electron-builder.yml` 将 `node-pty` 作为 native 模块正确打包
3. 新建 `src/main/terminal-manager.js`:
   - `createTerminal(options)`: 创建 PTY 进程，返回 terminal ID
   - `writeToTerminal(id, data)`: 向 PTY 写入
   - `resizeTerminal(id, cols, rows)`: 调整 PTY 尺寸
   - `destroyTerminal(id)`: 销毁 PTY
   - `getLogStream()`: 获取后端日志流（ring buffer）
4. 修改 `src/main/index.js`:
   - 后端 stdout/stderr 同时写入 log ring buffer (保留最近 10000 行)
   - 注册终端相关 IPC handlers

**文件变更**:
- 新建 `src/main/terminal-manager.js`
- 修改 `src/main/index.js` (添加 IPC + log buffer)
- 修改 `package.json` (添加依赖)
- 修改 `electron-builder.yml` (native 模块配置)

**预计改动量**: 中

---

#### Phase 7B: 渲染进程 — 终端面板 UI

**工作内容**:
1. 新建 `src/renderer/src/components/terminal/TerminalPanel.vue`:
   - 面板容器: 固定在主内容区底部
   - 顶部拖拽手柄 (4px, cursor: ns-resize)
   - 标签栏: "后端日志" (固定) + 动态终端标签 + "+" 按钮 + 折叠按钮
   - 内容区: xterm.js Terminal 挂载点
2. 新建 `src/renderer/src/components/terminal/TerminalTab.vue`:
   - 管理单个 xterm.js 实例
   - 处理 IPC 数据接收和键盘输入发送
3. 修改 `src/renderer/index.html`:
   - 添加终端面板容器 DOM
   - 添加终端面板相关 CSS
   - 状态栏添加"终端"切换按钮

**面板 HTML 结构**:
```html
<div class="terminal-panel" id="terminal-panel">
  <div class="terminal-resize-handle" id="terminal-resize-handle"></div>
  <div class="terminal-panel-header">
    <div class="terminal-tabs" id="terminal-tabs">
      <div class="terminal-tab active">后端日志</div>
    </div>
    <div class="terminal-panel-actions">
      <button class="terminal-action-btn" id="terminal-new-btn" title="新建终端">+</button>
      <button class="terminal-action-btn" id="terminal-close-btn" title="关闭">×</button>
      <button class="terminal-action-btn" id="terminal-toggle-btn" title="折叠">▼</button>
    </div>
  </div>
  <div class="terminal-content" id="terminal-content"></div>
</div>
```

**样式规范**:
```css
.terminal-panel {
  background: #1e1e1e;
  border-top: 1px solid #333;
  display: flex;
  flex-direction: column;
}

.terminal-panel-header {
  height: 36px;
  background: #252526;
  border-bottom: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
}

.terminal-tab {
  padding: 4px 12px;
  font-size: 12px;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.terminal-tab.active {
  color: #fff;
  border-bottom-color: #0078d4;
}
```

**预计改动量**: 大

---

#### Phase 7C: 后端日志标签

**工作内容**:
1. "后端日志" 标签为只读 xterm 终端实例
2. 主进程启动 DSA 服务时自动推送日志到渲染进程
3. 打开日志标签时，先接收 ring buffer 历史，再接收实时流
4. 日志高亮: stderr 用红色/黄色，stdout 用默认色
5. ANSI 颜色代码原样传递给 xterm (uvicorn 自带彩色输出)

**IPC 接口**:
```javascript
// 预加载脚本
subscribeLogs: () => ipcRenderer.invoke('terminal-subscribe-logs'),
onTerminalData: (callback) => ipcRenderer.on('terminal-data', (e, payload) => callback(payload)),
```

**预计改动量**: 小

---

#### Phase 7D: 交互式系统终端

**工作内容**:
1. 点击"+"创建新终端标签
2. 默认 shell:
   - Windows: `powershell.exe`
   - macOS: 环境变量 `$SHELL` 或 `/bin/zsh`
   - Linux: 环境变量 `$SHELL` 或 `/bin/bash`
3. 终端 cwd 默认为 `backend/` 目录
4. 终端 env 注入:
   - `VIRTUAL_ENV` 指向 `backend/.venv`
   - `PATH` 前置 `backend/.venv/bin` (Unix) 或 `backend/.venv/Scripts` (Windows)
   - 等效于自动激活 uv 创建的虚拟环境
5. 终端启动后自动显示提示: `(prophet-backend) $ ` 表示已在虚拟环境中
6. 支持 Ctrl+C 中断、Ctrl+D 关闭

**UV 环境激活策略**:
```javascript
function getTerminalEnv(backendDir) {
  const venvDir = path.join(backendDir, '.venv')
  const isWin = process.platform === 'win32'
  const binDir = isWin ? path.join(venvDir, 'Scripts') : path.join(venvDir, 'bin')
  
  return {
    ...process.env,
    VIRTUAL_ENV: venvDir,
    PATH: `${binDir}${path.delimiter}${process.env.PATH}`,
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1'
  }
}
```

**预计改动量**: 中

---

#### Phase 7E: 面板交互 — 折叠/展开/拖拽

**工作内容**:
1. 拖拽调整高度:
   - 顶部 resize handle (4px) 可上下拖拽
   - 拖拽时更新 WebContentsView bounds (主视图高度缩减)
   - 通过 IPC 通知主进程更新视图边界
2. 折叠/展开:
   - 状态栏添加终端图标按钮 (▪ 终端)
   - 点击切换 `terminalPanelVisible`
   - 展开时恢复上次高度
3. 状态持久化:
   - `terminalPanelHeight` 保存到 localStorage
   - `terminalPanelVisible` 保存到 localStorage
4. 主进程 `updateWebViewBounds()` 修改:
   - 当终端面板可见时，主视图高度减去终端面板高度

**updateWebViewBounds 修改逻辑**:
```javascript
function updateWebViewBounds(window, webView) {
  const [width, height] = mainWindow.getContentSize()
  const rightPanelWidth = agentPanelVisible ? currentAgentPanelWidth : 0
  const leftPanelWidth = explorerPanelVisible ? currentExplorerPanelWidth : 0
  const topOffset = getTopOffset()
  const bottomOffset = STATUS_BAR_HEIGHT + (terminalPanelVisible ? currentTerminalPanelHeight : 0)
  
  webView.setBounds({
    x: ACTIVITY_BAR_WIDTH + leftPanelWidth,
    y: topOffset,
    width: width - ACTIVITY_BAR_WIDTH - leftPanelWidth - rightPanelWidth,
    height: height - topOffset - bottomOffset
  })
}
```

**预计改动量**: 中

---

### 7.5 IPC 接口汇总

| 接口 | 方向 | 说明 |
|------|------|------|
| `terminal-create` | renderer → main (invoke) | 创建新 PTY 终端，返回 `{ id, pid }` |
| `terminal-input` | renderer → main (send) | 向指定终端写入数据 |
| `terminal-resize` | renderer → main (send) | 调整终端 cols/rows |
| `terminal-destroy` | renderer → main (send) | 销毁终端 |
| `terminal-subscribe-logs` | renderer → main (invoke) | 订阅后端日志，返回历史缓冲 |
| `terminal-data` | main → renderer (send) | 终端/日志数据输出 |
| `terminal-exit` | main → renderer (send) | 终端进程退出通知 |
| `toggle-terminal-panel` | renderer → main (send) | 切换终端面板可见性 |
| `resize-terminal-panel` | renderer → main (send) | 调整终端面板高度 |

### 7.6 实施顺序

```
Phase 7A: 基础设施 (依赖 + PTY 管理 + IPC)
    │
    ├─→ Phase 7B: 终端面板 UI (HTML + CSS + 标签管理)
    │       │
    │       ├─→ Phase 7C: 后端日志标签 (只读日志流)
    │       │
    │       └─→ Phase 7D: 交互式终端 (PTY + uv 环境)
    │
    └─→ Phase 7E: 面板交互 (折叠/展开/拖拽/bounds 更新)
```

**推荐实施顺序**: 7A → 7E → 7B → 7C → 7D

**理由**:
1. 7A 安装依赖并搭建主进程 PTY 管理基础
2. 7E 先解决布局和 bounds 计算（面板占位），确保终端面板不会遮挡主视图
3. 7B 构建 UI 骨架
4. 7C 后端日志功能最简单（只读），先实现验证数据流
5. 7D 交互终端涉及 PTY 双向通信，最后实现

### 7.7 注意事项

- **node-pty 编译**: 需要 `node-gyp` 环境，Windows 需安装 Visual Studio Build Tools
- **electron-rebuild**: `node-pty` 需要针对 Electron 版本重编译 (`npx electron-rebuild`)
- **安全性**: PTY 终端不应暴露给远程访问，仅本地使用
- **内存管理**: ring buffer 限制为 10000 行，防止内存泄漏
- **编码**: Windows 下 PowerShell 可能输出 GBK/CP936，需正确处理编码转换
- **xterm.js 主题**: 使用 VS Code Dark 配色方案以保持视觉一致