# 标的浏览器 (Symbol Browser) 开发计划

## 一、需求概述

在交易模式页面中新增一个**固定标签页**——"标的浏览器"，用于浏览和操作所有支持的交易标的（虚拟货币、A股、期货等）。

### 核心需求
1. 交易模式中的固定标签页，显示所有支持的交易标的
2. 不同类型标的来自不同数据源（Binance、AKShare、TickFlow 等）
3. 顶部有标的类型选择器，选中后下方列出对应标的列表
4. 标的列表 item 支持右键菜单（在图表中打开、市场分析等）
5. 统一数据层：本地缓存 + 数据中转，提供统一接口、降低请求频率
6. 兼容问股、市场分析等功能的数据需求

---

## 二、系统架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Renderer (前端)                                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  标的浏览器 UI     │    │  TradingView     │    │  市场分析 UI   │  │
│  │  (SymbolBrowser)  │    │   (Chart.vue)    │    │              │  │
│  └────────┬─────────┘    └────────┬─────────┘    └──────┬───────┘  │
│           │                       │                      │          │
│           └───────────────────────┼──────────────────────┘          │
│                                   │                                  │
│                    ┌──────────────▼──────────────┐                   │
│                    │   Unified Data Service       │                   │
│                    │   (前端统一数据服务层)         │                   │
│                    └──────────────┬──────────────┘                   │
├───────────────────────────────────┼─────────────────────────────────┤
│                        IPC / HTTP API                                │
├───────────────────────────────────┼─────────────────────────────────┤
│                     Backend (Python)                                  │
│                    ┌──────────────▼──────────────┐                   │
│                    │   Market Data Gateway        │                   │
│                    │   (统一市场数据网关)           │                   │
│                    ├─────────────────────────────┤                   │
│                    │   Local Cache (SQLite/JSON)  │                   │
│                    ├─────────┬─────────┬─────────┤                   │
│                    │ Binance │ AKShare │TickFlow  │                   │
│                    │ Adapter │ Adapter │ Adapter  │                   │
│                    └─────────┴─────────┴─────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、分阶段开发计划

### Phase 1：后端统一市场数据网关 (Market Data Gateway)

**目标**：建立统一的标的列表与行情数据 API

#### 1.1 定义统一数据模型

文件：`backend/api/v1/schemas/market.py`

```python
# 标的信息
class SymbolInfo:
    symbol: str          # 标的代码 (如 "BTCUSDT", "600519", "IF2406")
    name: str            # 中文名称/英文名称
    market_type: str     # crypto | cn_stock | cn_futures | hk_stock | us_stock
    exchange: str        # binance | sse | szse | cffex | hkex | nasdaq
    data_source: str     # binance | akshare | tickflow
    base_currency: str   # 计价货币 (USDT, CNY, HKD, USD)
    status: str          # trading | halted | delisted

# K线数据 (统一格式，兼容 TradingView Charting Library)
class KLineData:
    timestamp: int       # Unix 毫秒时间戳
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float      # 成交额 (可选)
```

#### 1.2 构建数据源适配器

基于已有的 `backend/data_provider/` 进行扩展：

| 适配器 | 数据源 | 覆盖市场 | 状态 |
|--------|--------|----------|------|
| BinanceAdapter | Binance REST/WS | 虚拟货币 | 已有(前端)，需后端化 |
| AKShareAdapter | akshare | A股/期货/ETF | 已有(`akshare_fetcher.py`)，需扩展标的列表接口 |
| TickFlowAdapter | TickFlow API | A股/期货(实时) | 待开发 |

#### 1.3 本地缓存层

文件：`backend/src/services/market_cache.py`

- **标的列表缓存**：每日更新，SQLite 存储
- **K线数据缓存**：按标的+周期缓存，增量更新
- **缓存策略**：
  - 标的列表：TTL 24h，启动时预加载
  - 日K线：盘后批量拉取，盘中不更新
  - 分钟K线：TTL 5min，按需拉取
  - 实时行情：不缓存，直连数据源

#### 1.4 API 端点设计

文件：`backend/api/v1/endpoints/market.py`

```
GET /api/v1/market/types                    # 获取支持的标的类型列表
GET /api/v1/market/symbols?type=cn_stock    # 获取某类型下的标的列表
GET /api/v1/market/symbols/search?q=茅台    # 搜索标的
GET /api/v1/market/kline?symbol=600519&period=1d&start=...&end=...  # K线数据
GET /api/v1/market/realtime?symbols=600519,000001  # 实时行情（批量）
```

---

### Phase 2：前端标的浏览器 UI

**目标**：实现标的浏览器固定标签页

#### 2.1 创建标的浏览器页面

新建文件：
- `src/renderer/symbol-browser.html` — 入口 HTML
- `src/renderer/src/symbol-browser.js` — Vue 挂载入口
- `src/renderer/src/SymbolBrowser.vue` — 主组件

#### 2.2 UI 布局

```
┌─────────────────────────────────────────┐
│  [标的类型选择器 ▼]   [搜索框 🔍]        │
├─────────────────────────────────────────┤
│  标的列表 (虚拟列表，支持大量数据)        │
│  ┌─────────────────────────────────────┐│
│  │ BTCUSDT  │ Bitcoin/USDT │ $67,234  ││
│  │ ETHUSDT  │ Ethereum/USDT│ $3,456   ││
│  │ ...      │              │          ││
│  └─────────────────────────────────────┘│
│                                         │
│  右键菜单:                               │
│  ├─ 📈 在图表中打开                      │
│  ├─ 🔍 市场分析                          │
│  ├─ ⭐ 添加到自选                        │
│  └─ 📋 复制代码                          │
└─────────────────────────────────────────┘
```

#### 2.3 组件拆分

| 组件 | 职责 |
|------|------|
| `SymbolBrowser.vue` | 主容器，管理状态 |
| `MarketTypeSelector.vue` | 顶部标的类型下拉选择 |
| `SymbolSearchBar.vue` | 搜索框，支持实时过滤 |
| `SymbolList.vue` | 虚拟滚动列表，展示标的 |
| `SymbolContextMenu.vue` | 右键菜单 |

#### 2.4 固定标签页集成

修改 `src/main/index.js`：
- 交易模式启动时，自动创建 "标的浏览器" 作为第一个固定标签页（不可关闭）
- 固定标签页样式区别于普通标签页（如无关闭按钮，置于最左侧）

---

### Phase 3：前端统一数据服务层

**目标**：为 TradingView Charting Library 和其他 UI 组件提供统一数据接口

#### 3.1 统一数据服务

新建文件：`src/renderer/src/service/marketDataService.ts`

```typescript
interface IMarketDataService {
  // 标的列表
  getMarketTypes(): Promise<MarketType[]>
  getSymbols(marketType: string): Promise<SymbolInfo[]>
  searchSymbols(query: string): Promise<SymbolInfo[]>

  // K线数据 (兼容 TradingView UDF 格式)
  getKLineData(symbol: string, period: string, from: number, to: number): Promise<KLineData[]>

  // 实时行情
  subscribeRealtime(symbols: string[], callback: (data: RealtimeQuote) => void): void
  unsubscribeRealtime(symbols: string[]): void
}
```

#### 3.2 数据源路由

根据标的类型自动路由到对应后端 API 或直连数据源：
- **虚拟货币**：直连 Binance WS（已有前端实现，保留以降低延迟）
- **A股/期货/ETF**：通过后端 Market Data Gateway 获取
- **港股/美股**：通过后端 Market Data Gateway 获取

#### 3.3 TradingView DataFeed 适配

新建文件：`src/renderer/src/service/dataSource/unified/datafeed.ts`

实现 TradingView Charting Library 的 `IBasicDataFeed` / `IDatafeedChartApi` 接口，内部调用 `marketDataService`，使 TradingView 图表可以展示任意数据源的 K 线。已有 Binance datafeed（`src/renderer/src/service/dataSource/binance/datafeed.ts`）可作为参考模板。

---

### Phase 4：右键菜单与功能集成

**目标**：实现标的操作菜单并打通各功能模块

#### 4.1 右键菜单操作

| 操作 | 实现方式 |
|------|----------|
| 在图表中打开 | IPC 创建新 chart tab，传入 symbol + dataSource |
| 市场分析 | IPC 切换到 market_analyze 模式，传入 symbol |
| 添加到自选 | 写入本地 watchlist (localStorage / SQLite) |
| 复制代码 | clipboard API |

#### 4.2 Chart.vue 改造

修改 `Chart.vue` / `KLineChartContainer.vue`：
- 支持通过 URL 参数或 IPC 消息接收 `symbol` + `dataSource`
- 根据 `dataSource` 类型选择对应的 DataFeed 实例
- 标题栏显示当前标的名称

---

### Phase 5：自选列表与搜索增强

**目标**：完善用户体验

#### 5.1 自选列表
- 本地持久化存储（SQLite / localStorage）
- 在标的浏览器中新增 "自选" 分类
- 支持拖拽排序

#### 5.2 搜索增强
- 支持代码、名称、拼音首字母搜索
- 搜索结果高亮
- 历史搜索记录

#### 5.3 实时行情展示
- 列表中显示最新价、涨跌幅
- 颜色标注涨跌（红涨绿跌 / 可配置）
- 开盘时间段自动刷新

---

## 四、技术要点

### 4.1 数据源对比

| 数据源 | 市场 | 获取方式 | 频率限制 | 当前状态 |
|--------|------|----------|----------|----------|
| Binance | 虚拟货币 | REST + WebSocket | 宽松 | ✅ 前端已接入 |
| AKShare | A股/期货/ETF | Python 库（爬虫） | 需节流(2-5s/req) | ✅ 后端已有 fetcher |
| TickFlow | A股/期货 | REST API | 需付费 Key | 🔲 待接入 |
| OKX | 虚拟货币 | REST + WebSocket | 宽松 | ✅ 前端已接入 |

### 4.2 缓存策略设计

```
标的列表缓存：
├─ 存储：SQLite (backend/data/market_cache.db)
├─ 更新频率：每日首次启动时拉取
├─ 虚拟货币：从 Binance exchangeInfo 获取
├─ A股：从 AKShare stock_zh_a_spot_em 获取
└─ 期货：从 AKShare futures_main_sina 获取

K线数据缓存：
├─ 存储：SQLite (按 symbol 分表)
├─ 日线：盘后增量更新
├─ 分钟线：TTL 5分钟，LRU 淘汰
└─ 最大缓存：500MB (可配置)
```

### 4.3 与现有系统的兼容

| 现有模块 | 集成方式 |
|----------|----------|
| TradingView Charting Library (前端图表) | 通过 unified datafeed 适配，支持切换 symbol |
| 后端 market_analyzer | 共享 `data_provider` 层，无需改动 |
| 后端 stock_analyzer | 共享 `data_provider` 层，无需改动 |
| 问股功能 (agent) | 通过 Market Data Gateway API 获取数据 |
| Bot (Telegram/飞书) | 共享后端 `data_provider` 层 |

---

## 五、开发优先级与里程碑

| 里程碑 | 内容 | 依赖 |
|--------|------|------|
| **M1** | 后端 Market Data Gateway API（标的列表 + K线） | 无 |
| **M2** | 前端标的浏览器 UI（固定标签页 + 列表 + 搜索） | M1 |
| **M3** | 前端统一数据服务 + TradingView 多数据源 DataFeed | M1 |
| **M4** | 右键菜单 + 图表打开 + 市场分析联动 | M2, M3 |
| **M5** | 自选列表 + 实时行情 + 搜索增强 | M4 |
| **M6** | TickFlow 数据源接入 + 缓存优化 | M1 |

---

## 六、文件变更清单（预估）

### 新增文件
```
backend/
├─ api/v1/endpoints/market.py          # 市场数据 API
├─ api/v1/schemas/market.py            # 数据模型定义
├─ src/services/market_cache.py        # 缓存服务
├─ src/services/market_gateway.py      # 数据网关服务
└─ data/market_cache.db                # SQLite 缓存数据库

src/renderer/
├─ symbol-browser.html                 # 标的浏览器入口
├─ src/symbol-browser.js               # Vue 挂载
├─ src/SymbolBrowser.vue               # 主组件
├─ src/components/MarketTypeSelector.vue
├─ src/components/SymbolSearchBar.vue
├─ src/components/SymbolList.vue
├─ src/components/SymbolContextMenu.vue
└─ src/service/
   ├─ marketDataService.ts             # 统一数据服务
   └─ dataSource/unified/
      └─ datafeed.ts                   # 统一 TradingView DataFeed
```

### 修改文件
```
src/main/index.js                      # 添加固定标签页逻辑
src/renderer/src/index.js              # 交易模式标签管理
src/renderer/src/Chart.vue             # 支持 symbol 参数
src/renderer/src/Chart.vue              # 多数据源 DataFeed 切换
src/preload/index.js                   # 新增 IPC 通道
backend/api/v1/__init__.py             # 注册新路由
electron.vite.config.mjs               # 新增页面入口
```

---

## 七、风险与注意事项

1. **AKShare 反爬**：已有节流与退避机制，标的列表接口调用频率低，风险可控
2. **数据一致性**：不同数据源的 K 线时间对齐（交易时段、时区）需统一处理
3. **性能**：A股 5000+ 标的，需虚拟列表 + 搜索索引，避免卡顿
4. **后端启动**：标的浏览器依赖后端服务，需处理后端未启动时的 graceful fallback
5. **数据源切换**：从原来前端直连 Binance 切换到统一层时，确保虚拟货币体验不降级