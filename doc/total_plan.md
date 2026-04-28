总体开发计划
===========================

1. 标的列表
2. A股数据源
3. 行情数据本地缓存
4. ~~chart页的抉择：继续使用tvcl，清洗tvcl，使用lwcl，还是使用echart等全开源版本~~
   → **决定：使用 KLineChart 替换 TradingView Charting Library**（详见下方迁移计划）
5. 标的列表联动chart、大分析、小分析
6. 改名字，做icon

---

## 4. KLineChart 迁移开发计划

### 背景与决策

TradingView Charting Library 为商业专有软件，存在以下合规风险：
- 库文件通过 git submodule 内嵌分发（`src/renderer/public/tradingview/`，2000+ 文件）
- Electron 桌面应用**不满足免费使用条件**（仅限公开网站）
- 未经授权的再分发可能引发法律风险

**替代方案选择：KLineChart（klinecharts）**
- Apache 2.0 许可证，完全自由商用
- 专业金融K线图库，内置 30+ 技术指标 + 画线工具
- 零依赖，gzip 后仅 ~40KB
- 支持 `setDataLoader({ getBars, subscribeBar, unsubscribeBar })` 数据接入模式
- 中文文档完善：https://klinecharts.com

---

### 现有 TradingView 集成清单（需迁移/删除的文件）

| 文件 | 行数 | 说明 |
|------|------|------|
| `src/renderer/src/components/TVChartContainer.vue` | 239 | 核心图表容器，使用 `widget()` API |
| `src/renderer/src/Chart.vue` | 79 | 图表页面，管理数据源选择 |
| `src/renderer/src/service/dataSource/binance/datafeed.ts` | 370 | Binance 历史K线数据 |
| `src/renderer/src/service/dataSource/binance/streaming.ts` | 220 | Binance WebSocket 实时推送 |
| `src/renderer/src/service/dataSource/binance/helpers.ts` | 90 | Binance 工具函数 |
| `src/renderer/src/service/dataSource/binance/saveLoadAdapter.ts` | 96 | 图表状态存取（TradingView 专有） |
| `src/renderer/src/service/dataSource/okx/datafeed.ts` | 370 | OKX 历史K线数据 |
| `src/renderer/src/service/dataSource/okx/streaming.ts` | 220 | OKX WebSocket 实时推送 |
| `src/renderer/src/service/dataSource/okx/helpers.ts` | 75 | OKX 工具函数 |
| `src/renderer/src/service/dataSource/okx/datafeed_template.ts` | 44 | OKX datafeed 模板（可删除） |
| `src/renderer/src/components/Versions.vue` | 26 | 显示 TradingView 版本号 |
| `electron.vite.config.mjs` | - | `@tradingview` 路径别名 |
| `vite.browser.config.mjs` | - | `@tradingview` 路径别名 |
| `src/renderer/public/tradingview/` | 2000+ 文件 | TradingView 完整库（git submodule） |

---

### API 映射关系

| TradingView API | KLineChart 对应 API |
|-----------------|-------------------|
| `new widget(options)` | `init(domId, options)` |
| `widget.remove()` | `dispose(domId)` |
| `IExternalDatafeed.onReady()` | 不需要，直接配置 |
| `IExternalDatafeed.resolveSymbol()` | `chart.setSymbol({ ticker, ... })` |
| `IExternalDatafeed.getBars()` | `setDataLoader({ getBars: ({ type, timestamp, symbol, period, callback }) => ... })` |
| `IExternalDatafeed.subscribeBars()` | `setDataLoader({ subscribeBar: ({ symbol, period, callback }) => ... })` |
| `IExternalDatafeed.unsubscribeBars()` | `setDataLoader({ unsubscribeBar: ({ symbol, period }) => ... })` |
| `IExternalDatafeed.searchSymbols()` | 需自行实现搜索 UI |
| `TradingView.Bar { time, open, high, low, close, volume }` | `KLineData { timestamp, open, high, low, close, volume }` |
| `widget.activeChart().onSymbolChanged()` | 通过 `setSymbol()` 触发，监听自定义事件 |
| `widget.headerReady() / createButton()` | 自行实现工具栏 UI（Vue 组件） |
| `IExternalSaveLoadAdapter` | 自行实现本地存储（如需要） |
| `disabled_features / enabled_features` | KLineChart styles 配置 |
| `theme: 'Dark'` | `init(id, { styles: { ... } })` 或预置暗色主题 |

### 数据格式映射

```
TradingView Bar:                    KLineChart KLineData:
{                                   {
  time: 1517846400 (秒)       →       timestamp: 1517846400000 (毫秒)
  open: 7424.6                →       open: 7424.6
  high: 7511.3                →       high: 7511.3
  low: 6032.3                 →       low: 6032.3
  close: 7310.1               →       close: 7310.1
  volume: 224461              →       volume: 224461
}                                     turnover: (可选)
                                    }
```

---

### 开发阶段

#### Phase 1：基础架构搭建 ✅ 已完成

- [x] **1.1** ~~安装 klinecharts 依赖：`npm install klinecharts`~~ ✅ **源码集成（Fork + Git Submodule + Vite Alias）**
  - Fork 仓库：`https://github.com/jiafeng5513/KLineChart`
  - Submodule 路径：`libs/klinecharts/`（基于 `v9.8.12` 创建 `prophet-dev` 分支）
  - Vite alias：`'klinecharts' → 'libs/klinecharts/src/index.ts'`（Vite 直接编译 TS 源码）
  - 上游同步：`git remote upstream` → `https://github.com/klinecharts/KLineChart`
- [x] **1.2** 创建 `KLineChartContainer.vue` 组件，替代 `TVChartContainer.vue`
  - 使用 `init(domId, options)` 初始化图表
  - 配置暗色主题（对应原 `theme: 'Dark'`）
  - 配置时区 `Asia/Shanghai`
  - 实现 `onUnmounted` 中调用 `dispose()` 清理
- [x] **1.3** 修改 `Chart.vue`，替换组件引用
  - 将 `<TVChartContainer>` 替换为 `<KLineChartContainer>`
  - 调整 props 传递方式
- [x] **1.4** 移除 `electron.vite.config.mjs` 和 `vite.browser.config.mjs` 中的 `@tradingview` 别名
- [x] **1.5** 用静态数据验证图表基本渲染

#### Phase 2：数据源适配 ✅ 已完成

- [x] **2.1** 重构 Binance DataLoader
  - 改写为 `binance/dataLoader.ts`：实现 `applyNewData` + `setLoadDataCallback` + WebSocket 实时推送
  - 回调数据格式从 `TradingView.Bar` 改为 `KLineData`
- [x] **2.2** 重构 OKX DataLoader（结构与 Binance 对称）
  - 改写为 `okx/dataLoader.ts`
  - OKX 特殊处理：`instId` 格式（`BTC-USDT`）、API 返回倒序需 `.reverse()`
- [x] **2.3** 删除 `saveLoadAdapter.ts`（TradingView 专有）
- [x] **2.4** 删除 `okx/datafeed_template.ts`
- [x] **2.5** 端到端测试：Binance + OKX 历史数据加载 & 实时推送

#### Phase 3：功能补全与 UI ✅ 已完成

- [ ] **3.1** 实现标的搜索功能
  - KLineChart 无内置搜索栏，需自行实现搜索 UI（Element Plus 的 `el-autocomplete` 或自定义下拉）
  - 复用现有 `searchSymbols` 的 Binance/OKX API 调用逻辑
  - 搜索结果选中后调用 `chart.setSymbol()` 切换标的
- [x] **3.2** 技术指标面板
  - KLineChart 内置指标：MA, EMA, MACD, KDJ, RSI, BOLL, VOL 等
  - 使用 `chart.createIndicator(name, bindSeries, bindPane)` 添加指标
  - 实现指标选择器 UI（工具栏按钮 + 弹窗，支持主图/副图指标分类）
- [x] **3.3** 画线工具 — **Pro 级完整实现**
  - 内置 15 个 overlay + 自定义注册 17 个 Pro 扩展 overlay，共计 32 个绘图工具
  - 自定义扩展来源：从 [klinecharts/pro](https://github.com/klinecharts/pro)（Apache 2.0）移植至 Vue 3
  - 扩展文件：`src/renderer/src/utils/overlayExtensions.js`（`registerProOverlays()`）
  - 绘图工具栏 UI（Pro 风格）：
    - 5 组画线工具（直线 11 / 通道 2 / 几何 4 / 斐波那契 7 / 浪型 6），每组带 SVG 图标 + 二级弹出菜单
    - 磁吸模式（弱磁吸 / 强磁吸，下拉选择）
    - 锁定 / 可见性 / 删除全部
    - SVG 图标精灵表（`<symbol>` + `<use href>`），暗色主题滚动条样式
- [x] **3.4** 周期切换
  - 实现 `setPeriod({ span, type })` 调用
  - 周期映射：`1m / 5m / 15m / 1H / 4H / 1D / 3D / 1W / 1M`
- [x] **3.5** 实现标题同步（symbol 变化 → 通知父窗口/更新 tab 标题）

#### Phase 4：清理与测试

- [ ] **4.1** 移除 TradingView git submodule
  - `git submodule deinit src/renderer/public/tradingview`
  - `git rm src/renderer/public/tradingview`
  - 清理 `.gitmodules` 中相关条目
- [x] **4.2** 移除 `Versions.vue` 中 TradingView 版本引用（已改为显示 klinecharts 版本）
- [ ] **4.3** 清理所有 `/// <reference types="@tradingview/..." />` 类型引用
- [x] **4.4** 浏览器模式测试（`npm run dev:browser`）— 构建通过
- [ ] **4.5** Electron 模式测试（`npm run dev`）
- [ ] **4.6** 跨数据源测试：Binance ↔ OKX 切换
- [ ] **4.7** 打包测试（`npm run build:win`）

---

### 当前文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `libs/klinecharts/` | ✅ 新增 | Git Submodule，Fork 自 klinecharts v9.8.12 |
| `src/renderer/src/components/KLineChartContainer.vue` | ✅ 新增 | Pro 风格图表容器（~900 行），含顶部工具栏 + 画线侧栏 + 指标弹窗 |
| `src/renderer/src/utils/overlayExtensions.js` | ✅ 新增 | 17 个 Pro 自定义 overlay 注册（arrow, circle, rect, 斐波那契系列, 浪型系列等） |
| `src/renderer/src/service/dataSource/binance/dataLoader.ts` | ✅ 新增 | Binance 数据加载器（REST + WebSocket） |
| `src/renderer/src/service/dataSource/okx/dataLoader.ts` | ✅ 新增 | OKX 数据加载器（REST + WebSocket） |
| `src/renderer/src/Chart.vue` | ✅ 已改 | 引用 KLineChartContainer，管理数据源选择 |
| `src/renderer/src/components/Versions.vue` | ✅ 已改 | 显示 klinecharts 版本 |
| `electron.vite.config.mjs` | ✅ 已改 | klinecharts alias 替换 @tradingview |
| `vite.browser.config.mjs` | ✅ 已改 | klinecharts alias 替换 @tradingview |

---

### 预估工时

| 阶段 | 工作量 | 状态 |
|------|--------|------|
| Phase 1：基础架构 | 3~4 天 | ✅ 已完成 |
| Phase 2：数据源适配 | 4~5 天 | ✅ 已完成 |
| Phase 3：功能补全与 UI | 3~4 天 | ✅ 已完成（搜索功能待做） |
| Phase 4：清理与测试 | 2~3 天 | 🔄 进行中 |

### 剩余工作

1. **标的搜索 UI**（3.1）— 未开始
2. **移除 TradingView submodule**（4.1）— 需确认时机后执行
3. **清理 @tradingview 类型引用**（4.3）
4. **Electron 模式测试 + 跨数据源测试 + 打包测试**（4.5~4.7）

### 风险点

1. **Symbol 搜索体验降级**：TradingView 内置搜索栏功能丰富，KLineChart 需自行实现，初期体验可能不如原版
2. **图表状态持久化**：原 `saveLoadAdapter` 提供的图表布局保存/恢复功能需评估是否移植
3. ~~**KLineChart v10 仍为 beta**~~ → 已锁定 v9.8.12 源码集成，不受 npm 版本影响
4. ~~**画线工具覆盖度**~~ → 已通过 Pro 移植实现 32 个完整绘图工具，与 Pro 演示站完全对齐