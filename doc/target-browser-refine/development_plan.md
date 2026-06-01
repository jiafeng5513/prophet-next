# 标的浏览器重构开发计划

## 一、需求回顾

根据 [readme.md](readme.md) 中的描述，本次重构需解决以下问题：

1. **左侧侧边栏可视区域小**，每行信息有限 → 将完整标的浏览器移到独立 Tab 页
2. **缺乏排列、筛选功能** → 参考 TradingView 的多列表格 + 排序/筛选

### 目标效果

| 位置 | 功能 | 可关闭 |
|------|------|--------|
| 左侧侧边栏 | 仅保留**自选列表** | — |
| 交易模式 Tab | **首页** — 宏观指数概览 | 不可关闭，默认显示 |
| 交易模式 Tab | **标的浏览器** — 分板块浏览+排序筛选 | 不可关闭 |

---

## 二、数据可用性评估

对标 TradingView 的标的浏览器列项，评估各市场各数据源的数据可获取性：

### 2.1 列项 × 数据源矩阵

| 列项 | 加密货币 (Binance) | A股 (东财/TickFlow) | 港股 (TickFlow/Longbridge) | 美股 (TickFlow/Longbridge) |
|------|:---:|:---:|:---:|:---:|
| **代码** | ✅ exchangeInfo | ✅ | ✅ | ✅ |
| **名称** | ✅ exchangeInfo | ✅ | ✅ | ✅ |
| **最新价** | ✅ ticker/24hr | ✅ quotes | ✅ quotes | ✅ quotes |
| **涨跌幅** | ✅ priceChangePercent | ✅ change_pct | ✅ change_pct | ✅ change_pct |
| **成交量** | ✅ volume | ✅ volume | ✅ volume | ✅ volume |
| **成交额** | ✅ quoteVolume | ✅ amount | ✅ amount | ✅ amount |
| **相对成交量(量比)** | ⚠️ 需自行计算¹ | ✅ volume_ratio (东财) | ⚠️ 需自行计算 | ⚠️ 需自行计算 |
| **换手率** | ⚠️ 需流通量数据² | ✅ turnover_rate (东财) | ⚠️ TickFlow 有 | ⚠️ TickFlow 有 |
| **振幅** | ✅ 可从 high/low 计算 | ✅ amplitude (东财/TickFlow) | ✅ 可计算 | ✅ 可计算 |
| **总市值** | ❌ 无直接API³ | ✅ total_mv (东财) | ⚠️ TickFlow financials | ⚠️ TickFlow financials |
| **流通市值** | ❌ 无直接API | ✅ circ_mv (东财) | ⚠️ 部分 | ⚠️ 部分 |
| **P/E (市盈率)** | ❌ 不适用 | ✅ pe_ratio (东财) + TickFlow /financials/metrics | ⚠️ TickFlow | ⚠️ TickFlow |
| **P/B (市净率)** | ❌ 不适用 | ✅ pb_ratio (东财) | ⚠️ TickFlow | ⚠️ TickFlow |
| **摊薄每股收益(EPS)** | ❌ 不适用 | ✅ TickFlow /financials/metrics | ⚠️ TickFlow | ⚠️ TickFlow |
| **板块/行业** | ❌ | ⚠️ AKShare 可获取 | ❌ 暂无 | ❌ 暂无 |
| **分析师评级** | ❌ | ❌ 无免费源 | ❌ | ❌ |
| **52周最高/最低** | ⚠️ 需历史K线计算 | ✅ high_52w/low_52w | ⚠️ 需计算 | ⚠️ 需计算 |
| **60日涨跌幅** | ⚠️ 需历史K线计算 | ✅ change_60d (东财) | ⚠️ 需计算 | ⚠️ 需计算 |

> **注释：**
> 1. 量比 = 当前成交量 / 过去5日同一时段平均成交量，需缓存历史数据后本地计算
> 2. Binance 不直接提供流通量数据，需外部数据源 (如 CoinGecko/CoinMarketCap)
> 3. 加密货币市值数据需接入 CoinGecko API 或 CoinMarketCap API (免费额度有限)
>
> **数据源优先级：TickFlow (已付费) 为 A股/港股/美股首选数据源，东财(AKShare/Efinance)作为兜底。**

### 2.2 各数据源 API 能力总结

#### TickFlow (A股/港股/美股首选，已付费)
- `GET /v1/quotes` — 实时行情：last_price, volume, amount, high, low, open, prev_close, ext{change_pct, change_amount, amplitude, turnover_rate, name}
- `GET /v1/financials/metrics` — 核心财务指标：EPS、ROE、利润增长率、偿债能力等
- `GET /v1/financials/income` — 利润表
- `GET /v1/financials/capital` — 股本表（总股本、流通股本）
- Universe 标的池：CN_Equity_A, CN_ETF, CN_Index, US_Equity, HK_Equity
- WebSocket `/v1/ws/stream` — 实时行情推送
- **付费权限已开通**，可直接使用全部接口（含分钟K线、实时行情、财务数据、市场深度）

#### Binance (加密货币首选)
- `GET /api/v3/ticker/24hr` — 24h统计：priceChange, priceChangePercent, volume, quoteVolume, highPrice, lowPrice, lastPrice, count
- `GET /api/v3/ticker/price` — 最新价格
- `GET /api/v3/ticker/tradingDay` — 当日统计
- WebSocket `<symbol>@ticker` — 实时24h滚动数据推送

#### 东方财富 (A股兜底数据源 via AKShare/Efinance)
- 实时行情含：price, change_pct, volume, amount, volume_ratio, turnover_rate, amplitude, pe_ratio, pb_ratio, total_mv, circ_mv
- 数据全面但需节流 (2-5s/request)
- **定位：当 TickFlow 不可用时的降级兜底**

### 2.3 推荐列项配置 (按市场)

| 市场 | 推荐显示列 |
|------|-----------|
| **加密货币** | 代码、名称、最新价、涨跌幅、成交量、成交额(QuoteVolume)、24h最高、24h最低 |
| **A股** | 代码、名称、最新价、涨跌幅、成交量、量比、换手率、总市值、P/E、振幅 |
| **港股** | 代码、名称、最新价、涨跌幅、成交量、成交额、换手率、振幅 |
| **美股** | 代码、名称、最新价、涨跌幅、成交量、成交额、换手率、振幅 |

---

## 三、架构设计

### 3.1 整体架构变更

```
变更前:
┌──────────────┐    ┌────────────────────────────────┐
│  左侧侧边栏   │    │  交易模式 Tab 区域               │
│  (标的浏览器)  │    │  [Chart] [Chart2] ...          │
└──────────────┘    └────────────────────────────────┘

变更后:
┌──────────────┐    ┌─────────────────────────────────────────────────────┐
│  左侧侧边栏   │    │  交易模式 Tab 区域                                    │
│  (仅自选列表)  │    │  [📊首页] [🔍标的浏览器] [Chart1] [Chart2] ...        │
│              │    │   ↑不可关闭  ↑不可关闭    ↑可关闭                      │
└──────────────┘    └─────────────────────────────────────────────────────┘
```

### 3.2 新增页面组件

```
src/renderer/
├── home.html                          # 首页入口
├── market-browser.html                # 标的浏览器入口
├── src/
│   ├── home.js                        # 首页 Vue 挂载
│   ├── Home.vue                       # 首页主组件
│   ├── market-browser.js              # 标的浏览器 Vue 挂载
│   ├── MarketBrowser.vue              # 标的浏览器主组件
│   └── components/
│       ├── home/
│       │   ├── IndexCard.vue          # 指数卡片 (上证/深证/纳斯达克/道琼斯)
│       │   └── MarketOverview.vue     # 市场概览面板
│       └── market-browser/
│           ├── MarketTabs.vue         # 市场板块切换 (加密/A股/港股/美股)
│           ├── ColumnConfig.vue       # 列配置面板
│           ├── DataTable.vue          # 核心数据表格 (虚拟滚动+排序+筛选)
│           ├── FilterBar.vue          # 筛选工具栏
│           └── SortIndicator.vue      # 排序指示器
```

### 3.3 侧边栏改造

现有 `SymbolBrowser.vue` 精简为**纯自选列表**：
- 移除市场类型选择器 (MarketTypeSelector)
- 移除搜索功能 (移至标的浏览器 Tab)
- 仅保留自选列表 + 拖拽排序 + 实时价格
- 新增"在标的浏览器中打开"入口

---

## 四、分阶段开发计划

### Phase 1：首页 Tab（Home Page）

**目标**：创建不可关闭的首页固定标签页，展示宏观市场数据

#### 1.1 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1 | 创建首页 HTML 入口 | `src/renderer/home.html` | 独立 WebContentsView |
| 2 | 创建首页 Vue 组件 | `src/renderer/src/Home.vue` | 主布局 |
| 3 | 实现指数卡片组件 | `src/renderer/src/components/home/IndexCard.vue` | 显示单个指数实时数据 |
| 4 | 主进程注册首页 Tab | `src/main/index.js` | 交易模式启动时创建，不可关闭，默认激活 |
| 5 | 后端宏观指数 API | `backend/api/v1/endpoints/market.py` | 新增 `/api/v1/market/indices` 端点 |

#### 1.2 首页布局设计

```
┌─────────────────────────────────────────────────────────────┐
│  市场概览                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 上证综指  │  │ 深证成指  │  │ 纳斯达克  │  │ 道琼斯    │    │
│  │ 3,245.67 │  │10,876.54 │  │16,234.89 │  │38,456.12 │    │
│  │ +1.23%   │  │ -0.45%   │  │ +0.89%   │  │ +0.12%   │    │
│  │ [迷你图] │  │ [迷你图] │  │ [迷你图] │  │ [迷你图] │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 恒生指数  │  │ BTC/USDT │  │ ETH/USDT │  │ 创业板指  │    │
│  │18,234.56 │  │67,234.00 │  │ 3,456.78 │  │ 2,134.56 │    │
│  │ -0.34%   │  │ +2.45%   │  │ +1.67%   │  │ +0.78%   │    │
│  │ [迷你图] │  │ [迷你图] │  │ [迷你图] │  │ [迷你图] │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 指数数据源

| 指数 | 代码 | 数据源 | 备注 |
|------|------|--------|------|
| 上证综指 | 000001.SH | TickFlow / AKShare | 交易时段实时 |
| 深证成指 | 399001.SZ | TickFlow / AKShare | 交易时段实时 |
| 创业板指 | 399006.SZ | TickFlow / AKShare | 交易时段实时 |
| 恒生指数 | HSI | TickFlow / Longbridge | HK市场 |
| 纳斯达克 | .IXIC / ^IXIC | TickFlow / YFinance | US市场 |
| 道琼斯 | .DJI / ^DJI | TickFlow / YFinance | US市场 |
| BTC/USDT | BTCUSDT | Binance | 24h |
| ETH/USDT | ETHUSDT | Binance | 24h |

---

### Phase 2：标的浏览器 Tab（Market Browser）

**目标**：创建功能完整的标的浏览器固定标签页，支持多列排序和筛选

#### 2.1 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1 | 创建标的浏览器 HTML 入口 | `src/renderer/market-browser.html` | 独立 WebContentsView |
| 2 | 创建主组件 | `src/renderer/src/MarketBrowser.vue` | 板块切换 + 数据表格 |
| 3 | 实现市场板块切换 | `components/market-browser/MarketTabs.vue` | 加密/A股/港股/美股 Tab |
| 4 | 实现数据表格组件 | `components/market-browser/DataTable.vue` | 虚拟滚动 + 列排序 |
| 5 | 实现筛选工具栏 | `components/market-browser/FilterBar.vue` | 搜索 + 快捷筛选 |
| 6 | 实现列配置面板 | `components/market-browser/ColumnConfig.vue` | 用户自定义显示列 |
| 7 | 主进程注册标的浏览器 Tab | `src/main/index.js` | 不可关闭固定标签 |
| 8 | 后端增强实时行情批量接口 | `backend/api/v1/endpoints/market.py` | 支持排序/分页参数 |

#### 2.2 UI 布局设计

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [加密货币] [A股] [港股] [美股]          🔍搜索...  ⚙️列配置  📥筛选      │
├──────────────────────────────────────────────────────────────────────────┤
│  筛选条件: [市值>100亿 ×] [PE<30 ×] [涨幅>0 ×]              [清除全部]   │
├──────────────────────────────────────────────────────────────────────────┤
│  代码 ▼ │ 名称    │ 最新价 ▲ │ 涨跌幅  │ 成交量  │ 量比 │ 总市值  │ P/E │
├──────────┼─────────┼──────────┼─────────┼─────────┼──────┼─────────┼─────┤
│  600519  │ 贵州茅台 │ 1,856.00│ +2.34%  │ 23,456  │ 1.5  │ 23,302亿│28.6 │
│  000001  │ 平安银行 │   12.56 │ -0.79%  │156,789  │ 0.8  │  2,432亿│ 5.2 │
│  601398  │ 工商银行 │    5.23 │ +0.19%  │ 89,012  │ 1.2  │ 18,654亿│ 4.8 │
│  ...     │         │         │         │         │      │         │     │
├──────────────────────────────────────────────────────────────────────────┤
│  共 5,234 只 │ 已筛选 156 只 │ 刷新时间: 14:30:25                        │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 2.3 数据表格核心功能

| 功能 | 说明 |
|------|------|
| **虚拟滚动** | 5000+ 行数据流畅滚动，仅渲染可视区域 |
| **列排序** | 点击表头切换 升序/降序/默认，支持多列排序 |
| **列筛选** | 数值列支持范围筛选 (>、<、区间)，文本列支持搜索 |
| **列宽调整** | 拖动列边界调整列宽 |
| **列显隐** | 通过列配置面板选择要显示的列 |
| **列固定** | 代码/名称列固定在左侧不随横向滚动 |
| **自动刷新** | 交易时段按配置频率自动刷新价格数据 |
| **右键菜单** | 在图表中打开 / 添加到自选 / 市场分析 / 复制代码 |

#### 2.4 排序与筛选后端支持

新增/修改 API：

```
GET /api/v1/market/browser?type=cn_stock
    &sort=total_mv:desc,change_pct:desc
    &filter=total_mv>10000000000,pe_ratio<30
    &page=1&page_size=100
    &fields=symbol,name,price,change_pct,volume,volume_ratio,total_mv,pe_ratio
```

**设计要点**：
- 后端支持服务端排序和筛选（数据量大时前端排序性能不够）
- 前端在数据量 <500 时可纯前端排序，>500 时使用后端排序
- 分页加载，支持无限滚动

---

### Phase 3：侧边栏精简为自选面板

**目标**：将侧边栏从完整标的浏览器精简为轻量自选列表

#### 3.1 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1 | 移除 MarketTypeSelector | `SymbolBrowser.vue` | 不再需要市场类型切换 |
| 2 | 移除搜索栏 | `SymbolBrowser.vue` | 搜索功能移至标的浏览器 Tab |
| 3 | 侧边栏仅显示自选 | `SymbolBrowser.vue` | watchlist 直接显示 |
| 4 | 新增快捷入口 | `SymbolBrowser.vue` | "打开标的浏览器" 按钮 |
| 5 | 保留拖拽排序 | `SymbolList.vue` | 自选列表仍支持拖拽 |
| 6 | 保留实时价格 | `SymbolList.vue` | 保留价格/涨跌显示 |

---

### Phase 4：后端数据增强

**目标**：为标的浏览器提供完整的多维度数据

#### 4.1 任务清单

| # | 任务 | 说明 |
|---|------|------|
| 1 | 新增批量行情+估值接口 | 合并实时行情和财务数据为一个响应 |
| 2 | A股估值数据缓存 | PE/PB/市值等数据每日缓存，盘中不频繁请求 |
| 3 | 板块/行业数据接入 | AKShare 获取 A 股行业分类 |
| 4 | 加密货币扩展数据 | 接入 CoinGecko 获取 market_cap 等（可选） |
| 5 | 相对成交量计算服务 | 后端计算量比（需缓存5日分时成交量） |
| 6 | 52周高低点计算 | 基于日K线数据本地计算 |

#### 4.2 新增 API 设计

```python
# 标的浏览器专用批量数据接口
GET /api/v1/market/browser/data
    ?type=cn_stock
    &fields=price,change_pct,volume,volume_ratio,turnover_rate,total_mv,pe_ratio
    &sort=total_mv:desc
    &filter=total_mv>10000000000
    &offset=0&limit=100

Response:
{
    "total": 5234,
    "data": [
        {
            "symbol": "600519",
            "name": "贵州茅台",
            "price": 1856.00,
            "change_pct": 2.34,
            "volume": 23456,
            "volume_ratio": 1.5,
            "turnover_rate": 0.18,
            "total_mv": 2330200000000,
            "pe_ratio": 28.6
        },
        ...
    ],
    "updated_at": "2026-05-30T14:30:25+08:00"
}
```

#### 4.3 数据刷新策略

| 数据类别 | 刷新频率 | 存储 | 首选源 | 兜底源 |
|----------|----------|------|--------|--------|
| 价格/涨跌幅/成交量 | 5-8s (交易时段) | 内存 | TickFlow WebSocket | 东财轮询 |
| 量比/换手率 | 30s | 内存 | TickFlow quotes ext | 东财 |
| 总市值/流通市值 | 日频 (每日盘前) | SQLite | TickFlow financials/capital | 东财 |
| PE/PB/EPS | 季频 (财报发布) | SQLite | TickFlow financials/metrics | 东财 |
| 板块/行业 | 周频 | SQLite | AKShare 行业分类 | — |
| 52周高低 | 日频 | SQLite | TickFlow 日K线计算 | AKShare |

---

### Phase 5：前端性能优化

**目标**：确保 5000+ 行数据的流畅体验

#### 5.1 关键技术方案

| 方案 | 说明 |
|------|------|
| **虚拟滚动** | 仅渲染可视区 + 上下缓冲区 (参考现有 SymbolList.vue 的实现扩展) |
| **Web Worker 排序** | 大数据集排序在 Worker 中执行，不阻塞 UI |
| **增量更新** | 实时价格更新仅刷新变化的单元格，不重渲染整行 |
| **分片加载** | 首次加载 100 条 → 滚动时按需追加 |
| **列固定 (sticky)** | CSS `position: sticky` 实现左侧固定列 |
| **防抖刷新** | 批量行情推送合并后统一渲染 (requestAnimationFrame) |

---

## 五、技术选型

| 需求 | 选型 | 理由 |
|------|------|------|
| 数据表格 | 自研 (基于现有虚拟列表扩展) | 项目已有虚拟滚动实现，无需引入重型表格库 |
| 迷你图 (首页) | Canvas 手绘 / 轻量 sparkline 库 | 性能优于 SVG |
| 排序/筛选 UI | 自研 | 需求明确，无需引入额外依赖 |
| 数据通信 | HTTP REST + SSE/轮询 | 沿用现有架构，WebSocket 可选优化 |

---

## 六、里程碑与优先级

| 里程碑 | 内容 | 估计工作量 | 依赖 |
|--------|------|-----------|------|
| **M1** | 首页 Tab (宏观指数卡片) | 小 | 无 |
| **M2** | 标的浏览器 Tab 基础框架 (板块切换 + 表格骨架) | 中 | 无 |
| **M3** | 数据表格核心功能 (虚拟滚动 + 列排序) | 中 | M2 |
| **M4** | 后端批量数据 API + 估值数据缓存 | 中 | 无 |
| **M5** | 筛选功能 + 列配置 | 中 | M3, M4 |
| **M6** | 侧边栏精简为自选面板 | 小 | M2 |
| **M7** | 主进程 Tab 注册 + 固定标签逻辑 | 小 | M1, M2 |
| **M8** | 性能优化 + 增量更新 | 中 | M3 |

### 建议开发顺序

```
并行线 A (前端):  M1 → M2 → M3 → M5 → M6 → M8
并行线 B (后端):  M4
集成点:          M7 (在 M1+M2 完成后)
                 M5 (需要 M3+M4 均完成)
```

---

## 七、风险与注意事项

| 风险 | 缓解措施 |
|------|----------|
| A股 5000+ 标的全量实时行情请求压力大 | 分页加载 + 仅刷新可视区域标的的实时数据 |
| TickFlow 服务不可用/超时 | 自动降级到东财(AKShare/Efinance)兜底 |
| TickFlow API 配额耗尽 | 监控用量 + 非热门标的降低刷新频率 |
| Electron 多 WebContentsView 内存开销 | 首页/标的浏览器共用相同预加载脚本，减少重复 |
| 列排序+筛选在前端性能瓶颈 | 数据量 >500 时走后端排序，<500 纯前端 |

---

## 八、与现有功能的关系

| 现有功能 | 影响 | 处理方式 |
|----------|------|----------|
| 侧边栏 SymbolBrowser | 精简 | Phase 3 改造为纯自选面板 |
| Chart Tab 打开逻辑 | 无变化 | 标的浏览器复用现有 IPC 打开图表 |
| 搜索功能 | 迁移 | 从侧边栏移至标的浏览器 Tab |
| 实时行情轮询 | 增强 | 统一行情服务，支持批量订阅 |
| 右键菜单 | 复用 | SymbolContextMenu 组件复用 |


测试情况
1. [done]原有的侧边栏标的浏览器没有进行清理，只需保留自选功能
2. [done]默认打开首页，无需默认打开BTCUSDT的K线图
3. 市场概览中，恒生指数，纳斯达克，道琼斯这三个指数没有数值更新
4. [done]标的浏览器双击跳转打开K线图
5. [done]标的浏览器的列宽要能调整
6. [done]自选侧栏的展开和关闭参考vscode的主侧栏

清理遗留交互，以下交互与已有的右上角交互按钮功能重复，需要删除：
1. [done] 左侧自选窗口上方的+按钮和折叠按钮
2. [done] 点击交易模式的logo展开/关闭左侧自选按钮
3. [done] 右侧ai聊天窗口右上角的小机器人图标用于打开agent window
4. [done] 状态栏右下角打开终端的按钮
