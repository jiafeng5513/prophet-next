# HiveLogic 重命名 & 文件命名规范整理计划

> 目标：将项目名称从 Prophet / Prophet-Next 统一为 **HiveLogic**，并规范化全部源码文件命名风格。

---

## 一、当前现状分析

### 1.1 名称残留（需替换为 HiveLogic）

| 位置 | 当前内容 | 目标内容 |
|------|----------|----------|
| `src/main/index.js:63` | `prophet-config.json` | `hivelogic-config.json` |
| `src/main/index.js:1555` | `prophet-config.env` | `hivelogic-config.env` |
| `src/renderer/src/Settings.vue:1627` | `# Prophet DSA Config Export` | `# HiveLogic DSA Config Export` |
| `src/renderer/src/Settings.vue:1637` | `prophet-config.env` | `hivelogic-config.env` |
| `src/renderer/src/Settings.vue:1648` | `prophet-config.env` | `hivelogic-config.env` |
| `backend/data_provider/okx_fetcher.py:122` | `Prophet-Next/1.0` | `HiveLogic/1.0` |
| `backend/data_provider/binance_fetcher.py:147` | `Prophet-Next/1.0` | `HiveLogic/1.0` |
| `doc/multi_agent_enhancement_plan.md` | 多处 `prophet-next` | `HiveLogic` |
| `doc/klinechart_migration_plan.md:82` | `prophet-dev` 分支名 | 保留（Git 历史，仅注释说明已更名） |

> 注：`package.json`、`electron-builder.yml` 已更名完毕，无需修改。

### 1.2 当前文件命名风格总结

| 模块 | 当前风格 | 示例 |
|------|----------|------|
| **前端 Vue 组件** | PascalCase `.vue` | `KLineChartContainer.vue`, `NewsDetail.vue` |
| **前端 JS 入口** | camelCase `.js` | `chart.js`, `stockAnalysis.js` → 不一致(有 `stock-analysis.js` 吗?) |
| **前端 HTML** | kebab-case `.html` | `stock-analysis.html`, `symbol-browser.html` |
| **前端 TS 服务** | camelCase `.ts` | `datafeed.ts`, `marketDataService.ts`, `realtimeWSClient.ts` |
| **前端 CSS** | kebab-case `.css` | `style.css`, `layout.css` |
| **前端 composables** | camelCase `.js` | `useSidePanelWidth.js` |
| **后端 Python** | snake_case `.py` | `stock_analyzer.py`, `binance_fetcher.py` ✅ (已统一) |
| **后端 YAML 策略** | snake_case `.yaml` | `bull_trend.yaml`, `ma_golden_cross.yaml` ✅ |
| **主进程/preload** | camelCase `.js` | `index.js`, `terminal-manager.js` ← kebab 混入 |

---

## 二、目标命名规范

| 文件类型 | 规范 | 说明 |
|----------|------|------|
| **Vue 组件** (`.vue`) | **PascalCase** | 如 `NewsDetail.vue`、`SymbolList.vue` |
| **前端 JS/TS 模块** (非组件) | **camelCase** | 如 `dataLoader.ts`、`marketDataService.ts` |
| **前端 HTML 入口** | **kebab-case** | 如 `stock-analysis.html`、`symbol-browser.html` |
| **前端 CSS 文件** | **kebab-case** | 如 `base.css`、`layout.css` |
| **前端 composables** | **camelCase** (use 前缀) | 如 `useSidePanelWidth.js` |
| **Electron 主进程/preload** | **camelCase** | 如 `index.js`、`terminalManager.js` |
| **后端 Python** | **snake_case** | 已统一，无需改动 |
| **配置/文档** | **kebab-case** | 如 `electron-builder.yml`、`api-keys.md` |
| **资源文件(图片等)** | **snake_case 或 kebab-case** | 如 `hivelogic_logo.png` |

---

## 三、执行计划

### Phase 1: 名称替换（Prophet → HiveLogic）

**影响范围**: 7 个文件  
**风险等级**: 低（纯字符串替换）  
**预计工作量**: 小

| # | 文件 | 操作 |
|---|------|------|
| 1 | `src/main/index.js` | 替换 `prophet-config.json` → `hivelogic-config.json` |
| 2 | `src/main/index.js` | 替换 `prophet-config.env` → `hivelogic-config.env` |
| 3 | `src/renderer/src/Settings.vue` | 替换 3 处 Prophet 相关字符串 |
| 4 | `backend/data_provider/okx_fetcher.py` | User-Agent 替换 |
| 5 | `backend/data_provider/binance_fetcher.py` | User-Agent 替换 |
| 6 | `doc/multi_agent_enhancement_plan.md` | 文档更新（可选，低优先） |
| 7 | `doc/klinechart_migration_plan.md` | 添加注释说明已更名 |

### Phase 2: Electron 主进程文件命名规范化

**影响范围**: 1 个文件重命名  
**风险等级**: 中（需更新 import 路径）

| # | 当前文件名 | 目标文件名 | 原因 |
|---|-----------|-----------|------|
| 1 | `src/main/terminal-manager.js` | `src/main/terminalManager.js` | 统一为 camelCase |

### Phase 3: 前端 JS 入口文件命名规范化

**影响范围**: 需确认的文件  
**风险等级**: 中（HTML 中的 script 引用需同步更新）

当前前端入口文件已经是 camelCase 格式（`chart.js`, `home.js`, `settings.js` 等），但带连字符的如 `stock-analysis.js`、`symbol-browser.js` 需确认是否存在：

| # | 当前文件名 | 目标文件名 | 关联 HTML |
|---|-----------|-----------|-----------|
| 1 | `src/renderer/src/stock-analysis.js` (如存在) | `src/renderer/src/stockAnalysis.js` | `stock-analysis.html` 内 script src |
| 2 | `src/renderer/src/symbol-browser.js` (如存在) | `src/renderer/src/symbolBrowser.js` | `symbol-browser.html` 内 script src |

> 注：HTML 文件保持 kebab-case 不变（这是 Web 标准惯例）。

### Phase 4: 前端 Vue 组件子目录名称规范化

**影响范围**: 组件子目录  
**风险等级**: 低（目录名不影响运行，仅影响 import 路径可读性）

当前子目录使用 kebab-case（`cache-timeline/`, `symbol-browser/`），这在 Vue 生态中是常见惯例，**建议保留不变**。

### Phase 5: 文档文件命名规范化（可选）

当前 `doc/` 目录已统一使用 snake_case（如 `total_plan.md`、`api_keys.md`），**建议保留不变**或统一为 kebab-case。

| 方案 | 示例 |
|------|------|
| 方案 A：保持 snake_case（当前） | `api_keys.md`, `total_plan.md` |
| 方案 B：统一 kebab-case | `api-keys.md`, `total-plan.md` |

**建议**: 选择方案 A（保持现状），避免不必要的 Git 历史变动。

---

## 四、执行顺序与依赖关系

```
Phase 1 (名称替换)
    ↓
Phase 2 (主进程文件重命名)
    ↓
Phase 3 (前端入口文件重命名)
    ↓  
Phase 4 & 5 (可选，视需求决定)
```

### 注意事项

1. **Git 重命名追踪**: 使用 `git mv` 进行文件重命名以保留历史
2. **构建验证**: 每个 Phase 完成后运行 `npm run build` 验证无编译错误
3. **vite 配置**: 文件重命名后检查 `electron.vite.config.mjs` 和 `vite.browser.config.mjs` 中的路径引用
4. **import 路径**: 重命名文件后需全局搜索更新所有 import/require 引用
5. **用户数据迁移**: `prophet-config.json` 重命名需考虑已部署用户的旧文件兼容（建议代码中添加 fallback 读取旧文件名）

---

## 五、不需要修改的部分

以下已经符合规范，无需改动：

- ✅ `package.json` — name 已为 `hivelogic`
- ✅ `electron-builder.yml` — productName 已为 `HiveLogic`
- ✅ `HiveLogicWorkSpace/` 目录 — 已更名
- ✅ 后端 Python 文件 — 已全部使用 snake_case
- ✅ 后端 YAML 策略文件 — 已全部使用 snake_case
- ✅ Vue 组件 — 已全部使用 PascalCase
- ✅ 前端 TS 服务文件 — 已全部使用 camelCase
- ✅ Logo 资源 — `hivelogic_logo.png` 已更新
