# 自定义指标编辑器系统 — 开发计划

## 1. 背景与目标

### 1.1 现状问题

当前应用存在一个独立的"开发模式"（Activity Bar 顶层入口），本质是 Python 策略编辑器。该模式存在以下问题：

- 与交易、回测等模式平级，但使用频率低
- 名称"开发模式"易产生误解
- 侧边栏内容（文件树）与其他模式（自选列表）逻辑混乱
- 当前自定义指标（如 Vegas Channel）直接硬编码在源码中，用户无法自行创建/管理

### 1.2 目标

将"开发模式"重构为**自定义指标编辑器系统**：

1. 用户可通过 JS 代码编写自定义技术指标（类似 TradingView Pine Editor）
2. 自定义指标与内置指标分区展示，不混合
3. 编辑器为**独立弹出窗口**（参照 Agent Window 模式）
4. 支持热加载：编辑后立即应用到图表
5. 安全沙箱：用户代码不可访问系统 API
6. 支持外部编辑器（VS Code / Cursor）

### 1.3 设计决策

| 决策项 | 结论 |
|--------|------|
| 指标语言 | 仅 JavaScript（TradingView CustomIndicator 接口） |
| 编辑器形态 | 独立弹出窗口（非侧边栏/底部面板） |
| 应用机制 | 热加载（无需重新添加指标） |
| 安全模型 | Web Worker 沙箱隔离 |

---

## 2. 架构设计

### 2.1 系统全景

```
┌─────────────────────────────────────────────────────────────────┐
│                        主窗口 (图表页)                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  指标选择对话框                                        │        │
│  │  ┌──────────┬──────────────────────────────────────┐ │        │
│  │  │[内置指标] │ [自定义指标]                          │ │        │
│  │  ├──────────┴──────────────────────────────────────┤ │        │
│  │  │  Vegas Channel     [应用] [编辑▼]               │ │        │
│  │  │  My Custom RSI     [应用] [编辑▼]               │ │        │
│  │  │  ─────────────────────────────────              │ │        │
│  │  │  + 新建自定义指标                                │ │        │
│  │  └────────────────────────────────────────────────┘ │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                   │
│  状态栏: [</>] ← 编辑器窗口快速入口                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                    IPC: indicator:open-editor
                              ▼
┌─────────────── 指标编辑器窗口 (独立) ────────────────────────────┐
│  Prophet 指标编辑器                                [_] [□] [×]   │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                       │
│ 文件列表  │  Monaco Editor (JavaScript)                           │
│          │                                                       │
│ ▸ vegas/ │  export function create(PineJS) {                     │
│   index  │    return {                                           │
│ ▸ my-rsi/│      name: 'VegasChannel',                            │
│   index  │      metainfo: { ... },                               │
│          │      constructor: function() { ... }                  │
│          │    }                                                   │
│          │  }                                                    │
│          │                                                       │
│          ├───────────────────────────────────────────────────────┤
│          │  [▶ 应用到图表]  [✓ 验证]  [📤 外部编辑器]  状态: ✓   │
└──────────┴───────────────────────────────────────────────────────┘
```

### 2.2 模块划分

```
src/main/
├── indicatorEditorWindow.js     ← 编辑器窗口管理（参照 agentWindow.js）
├── indicatorManager.js          ← 指标文件扫描、读写、fs.watch

src/renderer/
├── indicator-editor.html        ← 编辑器窗口入口 HTML
├── src/
│   ├── indicatorEditor.ts       ← 编辑器窗口 Vue 挂载
│   ├── IndicatorEditor.vue      ← 编辑器主组件
│   ├── components/
│   │   └── indicator-editor/
│   │       ├── FileTree.vue     ← 左侧指标文件列表
│   │       ├── EditorPane.vue   ← Monaco 编辑器封装
│   │       └── Toolbar.vue      ← 底部工具栏（应用/验证/状态）
│   └── services/
│       └── indicatorSandbox.js  ← Web Worker 沙箱运行时

src/preload/
├── indicatorEditor.js           ← 编辑器窗口专用 preload

ProphetWorkSpace/
└── indicator/                   ← 用户指标存储目录
    ├── vegas-channel/
    │   ├── manifest.json
    │   └── index.js
    └── ...
```

### 2.3 IPC 通道设计

| 通道名 | 方向 | 参数 | 说明 |
|--------|------|------|------|
| `indicator:open-editor` | 渲染→主 | `{ indicatorId?: string }` | 打开编辑器窗口，可选定位到指定指标 |
| `indicator:list` | 渲染→主 | — | 获取所有自定义指标清单 |
| `indicator:read` | 渲染→主 | `{ id }` | 读取指定指标代码 |
| `indicator:save` | 编辑器→主 | `{ id, code, manifest }` | 保存指标代码 |
| `indicator:create` | 编辑器→主 | `{ name, id }` | 创建新指标（含模板） |
| `indicator:delete` | 编辑器→主 | `{ id }` | 删除指标 |
| `indicator:code-updated` | 主→图表渲染 | `{ id, code }` | 通知图表热加载 |
| `indicator:reload-result` | 图表渲染→主→编辑器 | `{ id, success, error? }` | 热加载结果反馈 |
| `indicator:open-external` | 编辑器→主 | `{ id }` | 用外部编辑器打开 |
| `indicator:file-changed` | 主→编辑器/图表 | `{ id }` | 外部编辑器修改触发 |

---

## 3. 文件存储规范

### 3.1 目录结构

```
ProphetWorkSpace/
└── indicator/
    ├── vegas-channel/
    │   ├── manifest.json
    │   └── index.js
    ├── my-custom-rsi/
    │   ├── manifest.json
    │   └── index.js
    └── volume-profile/
        ├── manifest.json
        └── index.js
```

### 3.2 manifest.json 格式

```json
{
  "name": "Vegas Channel",
  "id": "vegas-channel",
  "version": "1.0.0",
  "overlay": true,
  "description": "5条EMA组成的Vegas趋势通道",
  "author": "",
  "created": "2026-06-02T00:00:00Z",
  "modified": "2026-06-02T00:00:00Z"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 显示名称 |
| `id` | string | ✅ | 唯一标识（目录名一致） |
| `version` | string | ✅ | 语义化版本号 |
| `overlay` | boolean | ✅ | `true`=主图叠加，`false`=副图 |
| `description` | string | ❌ | 简短描述 |
| `author` | string | ❌ | 作者 |
| `created` | string | ❌ | 创建时间 ISO 8601 |
| `modified` | string | ❌ | 最后修改时间 |

### 3.3 index.js 接口规范

每个自定义指标必须导出一个工厂函数 `create(PineJS)`，返回符合 TradingView `CustomIndicator` 接口的对象：

```javascript
/**
 * @param {object} PineJS - TradingView PineJS 运行时对象
 * @returns {CustomIndicator}
 */
export function create(PineJS) {
  return {
    name: 'IndicatorName',
    metainfo: {
      _metainfoVersion: 53,
      id: 'IndicatorName@tv-basicstudies-1',
      name: 'IndicatorName',
      description: 'My Indicator',
      shortDescription: 'MI',
      is_price_study: true,       // true=主图, false=副图
      isCustomIndicator: true,
      linkedToSeries: true,
      format: { type: 'inherit' },
      plots: [ /* ... */ ],
      defaults: { /* ... */ },
      styles: { /* ... */ },
      inputs: [ /* ... */ ]
    },
    constructor: function () {
      this.main = function (context, inputCallback) {
        // 计算逻辑
        return [ /* plot values */ ]
      }
    }
  }
}
```

---

## 4. 安全沙箱设计

### 4.1 威胁模型

用户指标代码可能：
- 尝试访问 Node.js API（`require`, `process`, `__dirname`）
- 尝试网络请求（`fetch`, `XMLHttpRequest`, `WebSocket`）
- 执行死循环导致 UI 冻结
- 访问 DOM 或 Electron IPC

### 4.2 隔离方案：Web Worker + 受限 API

```javascript
// indicatorSandbox.js

class IndicatorSandbox {
  constructor() {
    this.worker = null
    this.timeout = 5000 // 5秒执行超时
  }

  /**
   * 验证并实例化指标代码
   * @param {string} code - 用户指标源代码
   * @param {Float64Array} ohlcv - K线数据 [open, high, low, close, volume] × N
   * @returns {Promise<{ success: boolean, plots?: number[][], error?: string }>}
   */
  async evaluate(code, ohlcv) {
    // 创建 Blob Worker（不加载外部脚本）
    const workerCode = this._buildWorkerCode(code)
    const blob = new Blob([workerCode], { type: 'application/javascript' })
    const url = URL.createObjectURL(blob)

    return new Promise((resolve, reject) => {
      const worker = new Worker(url)
      const timer = setTimeout(() => {
        worker.terminate()
        resolve({ success: false, error: '执行超时 (>5s)' })
      }, this.timeout)

      worker.onmessage = (e) => {
        clearTimeout(timer)
        worker.terminate()
        URL.revokeObjectURL(url)
        resolve(e.data)
      }

      worker.onerror = (e) => {
        clearTimeout(timer)
        worker.terminate()
        URL.revokeObjectURL(url)
        resolve({ success: false, error: e.message })
      }

      // 发送 OHLCV 数据（Transferable 零拷贝）
      worker.postMessage({ ohlcv }, [ohlcv.buffer])
    })
  }

  _buildWorkerCode(userCode) {
    return `
      // 禁止访问危险 API
      self.fetch = undefined;
      self.XMLHttpRequest = undefined;
      self.WebSocket = undefined;
      self.importScripts = undefined;

      // 提供受限的 PineJS.Std 子集
      const PineJS = {
        Std: {
          close: (ctx) => ctx._closeSeries,
          open: (ctx) => ctx._openSeries,
          high: (ctx) => ctx._highSeries,
          low: (ctx) => ctx._lowSeries,
          volume: (ctx) => ctx._volumeSeries,
          ema: (series, length) => { /* EMA 纯数学实现 */ },
          sma: (series, length) => { /* SMA 纯数学实现 */ },
          rsi: (series, length) => { /* RSI 纯数学实现 */ },
          // ... 其他安全数学函数
        }
      };

      self.onmessage = function(e) {
        try {
          ${userCode}

          // 调用用户的 create 函数
          const indicator = create(PineJS);
          // 验证接口合规性
          if (!indicator || !indicator.name || !indicator.metainfo) {
            self.postMessage({ success: false, error: '指标必须导出 create() 并返回含 name/metainfo 的对象' });
            return;
          }
          self.postMessage({ success: true, metainfo: indicator.metainfo });
        } catch (err) {
          self.postMessage({ success: false, error: err.message });
        }
      };
    `
  }
}
```

### 4.3 实际运行时的两层策略

| 场景 | 执行方式 | 说明 |
|------|----------|------|
| **验证/预览**（编辑器中点"验证"） | Web Worker 沙箱 | 完全隔离，纯计算验证 |
| **图表渲染**（正式应用） | TradingView `custom_indicators_getter` | 利用 TV 库自身的指标运行环境 |

图表中正式应用时，代码经过沙箱验证通过后，才注册到 `custom_indicators_getter`。TradingView 库本身的指标执行环境已经是受限的（只提供 PineJS.Std），不暴露 DOM/Node API。

### 4.4 安全检查清单（代码保存时静态分析）

保存时对代码执行正则静态扫描，拒绝包含以下内容的代码：

```javascript
const BLOCKED_PATTERNS = [
  /\brequire\s*\(/,
  /\bprocess\b/,
  /\b__dirname\b/,
  /\b__filename\b/,
  /\bglobal\b/,
  /\bwindow\b/,
  /\bdocument\b/,
  /\bfetch\s*\(/,
  /\bXMLHttpRequest\b/,
  /\bWebSocket\b/,
  /\beval\s*\(/,
  /\bFunction\s*\(/,
  /\bimportScripts\b/,
  /\belectron\b/i
]
```

---

## 5. 热加载流程

### 5.1 完整时序

```
用户在编辑器中修改代码
    │
    ▼ 点击 [▶ 应用到图表]
    │
    ├─→ 编辑器窗口: indicator:save { id, code }
    │       ↓ (IPC 到主进程)
    │
    ├─→ 主进程: indicatorManager
    │       ├─ 写入文件 ProphetWorkSpace/indicator/{id}/index.js
    │       ├─ 更新 manifest.modified 时间戳
    │       └─ 发送 indicator:code-updated { id, code } 到图表渲染进程
    │              ↓
    │
    └─→ 图表渲染进程:
            ├─ 1. 在 Web Worker 沙箱中验证新代码 (语法 + 接口检查)
            ├─ 2. 验证失败 → 回报错误，保持旧指标不变
            ├─ 3. 验证通过 → 从 custom_indicators_getter 注册表中替换
            ├─ 4. 调用 TV widget API 移除旧指标实例
            ├─ 5. 重新添加指标（新代码生效）
            └─ 6. 发送 indicator:reload-result { id, success } 回主进程
                      ↓
                 主进程转发到编辑器窗口
                      ↓
                 编辑器工具栏显示: "✓ 已应用" 或 "✗ 错误: ..."
```

### 5.2 外部编辑器触发热加载

```
外部编辑器保存文件
    │
    ▼ fs.watch 检测到变化
    │
    ├─→ 主进程: indicatorManager
    │       ├─ 读取新文件内容
    │       ├─ 发送 indicator:file-changed { id } 到编辑器窗口（刷新编辑器内容）
    │       └─ 发送 indicator:code-updated { id, code } 到图表渲染进程
    │              ↓
    └─→ （同上热加载流程 步骤 1-6）
```

### 5.3 防抖策略

- 外部编辑器的 `fs.watch` 变化事件做 **500ms debounce**
- 编辑器窗口内的"应用"按钮点击后进入 loading 状态，收到结果前禁用重复点击

---

## 6. 指标选择 UI 改造

### 6.1 图表页指标对话框改造

在现有指标选择对话框中新增 Tab：

```
┌─────────────────────────────────────┐
│  [内置指标]  [自定义指标]            │ ← 顶部 Tab 切换
├─────────────────────────────────────┤
│  🔍 搜索自定义指标...                │
├─────────────────────────────────────┤
│                                     │
│  📊 Vegas Channel                   │
│  5条EMA趋势通道 · v1.0.0           │
│  [应用到主图]  [编辑 ▼]             │
│  ────────────────────────────       │
│  📊 My Custom RSI                   │
│  自定义RSI变体 · v1.0.0            │
│  [应用到副图]  [编辑 ▼]             │
│                                     │
├─────────────────────────────────────┤
│  + 新建自定义指标                    │
└─────────────────────────────────────┘
```

### 6.2 编辑按钮下拉菜单

```
[编辑 ▼]
  ├─ 📝 内置编辑器     → 打开指标编辑器窗口并定位到该指标
  ├─ 🔗 外部编辑器     → 调用系统编辑器打开文件
  ├─ ───────────
  ├─ 📋 复制           → 复制指标到新名称
  └─ 🗑️ 删除           → 确认后删除
```

---

## 7. 编辑器窗口实现

### 7.1 窗口配置

参照 `agentWindow.js`，创建 `indicatorEditorWindow.js`：

```javascript
// 窗口参数
{
  width: 1100,
  height: 700,
  minWidth: 800,
  minHeight: 500,
  parent: mainWindowRef,
  modal: false,
  title: 'Prophet 指标编辑器',
  autoHideMenuBar: true,
  backgroundColor: '#1e1e1e',
  webPreferences: {
    preload: indicatorEditorPreloadPath,
    sandbox: true,        // 编辑器窗口本身启用沙箱
    contextIsolation: true
  }
}
```

### 7.2 编辑器窗口 UI 布局

```
┌──────────────────────────────────────────────────────────────┐
│  Prophet 指标编辑器                           [_] [□] [×]    │
├──────────┬───────────────────────────────────────────────────┤
│          │  vegas-channel / index.js                    [×]  │ ← 标签栏
│ 指标列表  ├───────────────────────────────────────────────────┤
│          │                                                   │
│ ● vegas  │   1│ /**                                          │
│   channel│   2│  * Vegas Channel 自定义技术指标               │
│           │   3│  */                                          │
│ ○ my-rsi │   4│ export function create(PineJS) {             │
│           │   5│   return {                                   │
│           │   6│     name: 'VegasChannel',                    │
│           │   7│     ...                                      │
│ ──────── │                                                   │
│ [+ 新建]  │                                                   │
│          │                                                   │
├──────────┴───────────────────────────────────────────────────┤
│  [▶ 应用到图表]  [✓ 验证语法]  [📤 外部编辑器]   状态: ✓ 就绪 │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 新建指标模板

点击"新建"时生成模板代码：

```javascript
/**
 * 自定义指标: ${name}
 * 创建时间: ${date}
 */
export function create(PineJS) {
  return {
    name: '${Name}',

    metainfo: {
      _metainfoVersion: 53,
      id: '${Name}@tv-basicstudies-1',
      name: '${Name}',
      description: '${name}',
      shortDescription: '${Name}',
      is_price_study: true,
      isCustomIndicator: true,
      linkedToSeries: true,
      format: { type: 'inherit' },

      plots: [
        { id: 'plot0', type: 'line' }
      ],

      defaults: {
        styles: {
          plot0: { linestyle: 0, linewidth: 2, plottype: 2, color: '#2196F3', visible: true }
        },
        inputs: {
          length: 20
        }
      },

      styles: {
        plot0: { title: 'Value', histogramBase: 0 }
      },

      inputs: [
        { id: 'length', name: 'Length', type: 'integer', defval: 20, min: 1, max: 500 }
      ]
    },

    constructor: function () {
      this.main = function (context, inputCallback) {
        this._context = context
        this._input = inputCallback

        var length = this._input(0)
        var close = this._context.new_var(PineJS.Std.close(this._context))

        return [
          PineJS.Std.sma(close, length, this._context)
        ]
      }
    }
  }
}
```

---

## 8. 外部编辑器集成

### 8.1 设置项

在设置页面中增加配置项：

```
外部代码编辑器:
  [自动检测 ▼]
    ├─ 自动检测（按优先级: Cursor → VS Code → 系统默认）
    ├─ Visual Studio Code
    ├─ Cursor
    └─ 自定义路径...  [浏览...]
```

### 8.2 实现逻辑

```javascript
// main process: indicatorManager.js

import { exec } from 'child_process'
import { shell } from 'electron'

function openInExternalEditor(filePath) {
  const editor = getConfiguredEditor() // 从 settings 读取

  switch (editor) {
    case 'auto':
      // 尝试顺序: cursor → code → 系统默认
      tryOpen('cursor', filePath) ||
      tryOpen('code', filePath) ||
      shell.openPath(filePath)
      break
    case 'vscode':
      exec(`code "${filePath}"`)
      break
    case 'cursor':
      exec(`cursor "${filePath}"`)
      break
    default:
      exec(`"${editor}" "${filePath}"`)
  }
}
```

### 8.3 文件监听

```javascript
import { watch } from 'fs'

// 监听整个 indicator 目录
const watcher = watch(indicatorDir, { recursive: true }, debounce((eventType, filename) => {
  if (!filename.endsWith('.js')) return
  const indicatorId = extractIdFromPath(filename)
  // 通知编辑器窗口和图表窗口
  notifyCodeChanged(indicatorId)
}, 500))
```

---

## 9. Activity Bar 改造

### 9.1 移除"开发模式"

从 Activity Bar 中移除 Developing 模式入口，对应修改：

- `src/main/index.js`: 移除 `modeState.developing` 及相关视图管理逻辑
- `src/renderer/index.html`: 移除 Activity Bar 中的 Developing 按钮
- `src/renderer/src/index.js`: 移除 developing 模式切换逻辑
- `src/renderer/python.html` + `src/renderer/src/python.js`: 保留文件但不再作为独立模式入口

### 9.2 新增编辑器入口

| 入口位置 | 方式 |
|----------|------|
| 图表页指标选择对话框 → 自定义指标 Tab → 编辑按钮 | 主要入口 |
| 主窗口底部状态栏 `</>` 按钮 | 快速入口 |
| 全局快捷键 `Ctrl+Shift+E` | 键盘入口 |

---

## 10. 迁移计划（Vegas Channel）

将现有硬编码的 Vegas Channel 迁移为用户自定义指标：

### 10.1 迁移步骤

1. 将 `src/renderer/src/components/indicators/vegas-channel.js` 的内容适配为新的 `create()` 接口
2. 创建 `ProphetWorkSpace/indicator/vegas-channel/manifest.json`
3. 创建 `ProphetWorkSpace/indicator/vegas-channel/index.js`
4. 修改 `TVChartContainer.vue` 中的 `custom_indicators_getter`：从硬编码导入改为动态加载

### 10.2 迁移后的代码加载方式

```javascript
// TVChartContainer.vue (改造后)
custom_indicators_getter: async function (PineJS) {
  // 从主进程获取所有已启用的自定义指标代码
  const indicators = await window.electronAPI.invoke('indicator:get-active-indicators')
  return indicators.map(ind => {
    // 在沙箱中实例化
    const factory = new Function('PineJS', `${ind.code}\nreturn create(PineJS);`)
    return factory(PineJS)
  })
}
```

---

## 11. 实施阶段

### Phase 1: 基础框架（优先）

| # | 任务 | 涉及文件 |
|---|------|----------|
| 1 | 创建指标存储目录结构 + manifest 规范 | `ProphetWorkSpace/indicator/` |
| 2 | 实现 `indicatorManager.js`（扫描、读写、监听） | `src/main/indicatorManager.js` |
| 3 | 创建编辑器窗口骨架（参照 agentWindow.js） | `src/main/indicatorEditorWindow.js` |
| 4 | 编辑器窗口 HTML + Vue 挂载 | `src/renderer/indicator-editor.html`, `indicatorEditor.ts` |
| 5 | IPC 通道注册 | `src/main/index.js`, `src/preload/` |

### Phase 2: 编辑器 UI

| # | 任务 | 涉及文件 |
|---|------|----------|
| 6 | 编辑器主组件 + 文件列表 | `IndicatorEditor.vue`, `FileTree.vue` |
| 7 | Monaco 编辑器集成（JS 模式 + 自动补全） | `EditorPane.vue` |
| 8 | 工具栏（应用/验证/外部编辑器） | `Toolbar.vue` |
| 9 | 新建指标模板生成 | 模板文件 |

### Phase 3: 运行时集成

| # | 任务 | 涉及文件 |
|---|------|----------|
| 10 | Web Worker 沙箱实现 | `indicatorSandbox.js` |
| 11 | 图表组件改造：动态加载自定义指标 | `TVChartContainer.vue` |
| 12 | 热加载逻辑实现 | 图表渲染进程 |
| 13 | 迁移 Vegas Channel 为自定义指标 | `ProphetWorkSpace/indicator/vegas-channel/` |

### Phase 4: UI 集成 & 收尾

| # | 任务 | 涉及文件 |
|---|------|----------|
| 14 | 图表页指标对话框增加"自定义指标" Tab | 指标选择组件 |
| 15 | 外部编辑器集成 + 设置项 | `indicatorManager.js`, 设置页 |
| 16 | 移除 Activity Bar "开发模式" | `index.js`, `index.html` |
| 17 | 状态栏 `</>` 入口按钮 | 主窗口渲染进程 |

---

## 12. 技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| TradingView `custom_indicators_getter` 不支持运行时动态更新 | 热加载可能需要重建 widget | 使用 `widget.remove()` + 重新创建的方式兜底 |
| Web Worker 中无法完整模拟 PineJS 上下文 | 沙箱验证可能漏检 | 验证分两层：Worker 做语法+接口检查，实际运行依赖 TV 库环境 |
| 用户代码质量差导致图表崩溃 | 影响正常使用 | try-catch 包裹 + 崩溃自动禁用该指标 + 提示用户 |
| 外部编辑器保存频繁触发热加载 | 性能抖动 | 500ms debounce + 仅在代码实际变化时触发 |
| Monaco Editor 包体积大 | 编辑器窗口加载慢 | 按需加载，仅加载 JS 语言支持 |

---

## 13. 后续扩展（不在当前范围）

- Python 指标支持（后端计算 → overlay 叠加）
- 指标市场/社区分享
- 指标版本管理（git-like diff）
- 指标单元测试框架
- 自定义策略（与回测系统联动）
