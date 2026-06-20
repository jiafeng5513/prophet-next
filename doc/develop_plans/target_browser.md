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

### Phase 1：后端统一市场数据网关 (Market Data Gateway) ✅ 已完成

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
| BinanceAdapter | Binance REST/WS | 虚拟货币 | ✅ 已完成(后端集成至 MarketGateway) |
| AKShareAdapter | akshare | A股/期货/ETF | ✅ 已完成(标的列表+K线已接入 MarketGateway) |
| TickFlowAdapter | TickFlow API | A股/期货(实时) | ⚠️ P0已完成(市场概览)，P1待Phase 6接入 |

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

### Phase 2：前端标的浏览器 UI ✅ 已完成

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

### Phase 3：前端统一数据服务层 ✅ 已完成

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

### Phase 4：右键菜单与功能集成 ✅ 已完成

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

### Phase 5：自选列表与搜索增强 ✅ 已完成

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

| 数据源 | 市场 | 获取方式 | 频率限制 | 当前状态 | 优先级 |
|--------|------|----------|----------|----------|--------|
| TickFlow | A股/ETF/港股/美股 | REST + WebSocket + SDK | 付费按套餐限额 | ✅ 已有P0接口 | ⭐ CN首选 |
| Binance | 虚拟货币 | REST + WebSocket | 宽松 | ✅ 前端已接入 | ⭐ Crypto首选 |
| Tushare | A股/期货/ETF | REST API | 需积分 | ✅ 后端已有 fetcher | 第2优先级 |
| AKShare | A股/期货/ETF | Python 库（爬虫） | 需节流(2-5s/req) | ✅ 后端已有 fetcher | 第3优先级(兜底) |
| BaoStock | A股 | Python 库 | 较宽松 | ✅ 后端已有 fetcher | 第4优先级 |
| Efinance | A股 | Python 库 | 较宽松 | ✅ 后端已有 fetcher | 第5优先级 |
| OKX | 虚拟货币 | REST + WebSocket | 宽松 | ✅ 前端已接入 | Crypto第2优先级 |
| Longbridge | 美股/港股 | REST API | 需付费 | ✅ 后端已有 fetcher | 港股/美股兜底 |

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

| 里程碑 | 内容 | 依赖 | 状态 |
|--------|------|------|------|
| **M1** | 后端 Market Data Gateway API（标的列表 + K线） | 无 | ✅ 完成 |
| **M2** | 前端标的浏览器 UI（固定标签页 + 列表 + 搜索） | M1 | ✅ 完成 |
| **M3** | 前端统一数据服务 + TradingView 多数据源 DataFeed | M1 | ✅ 完成 |
| **M4** | 右键菜单 + 图表打开 + 市场分析联动 | M2, M3 | ✅ 完成 |
| **M5** | 自选列表 + 实时行情 + 搜索增强 | M4 | ✅ 完成 |
| **M6** | 多数据源优先级链 + TickFlow 深度接入 | M1 | ✅ 完成 |
| **M7** | WebSocket 实时推送 + 五档行情 | M6 | ✅ 已完成 |
| **M8** | 港股/美股市场接入 + 财务数据 | M6 | ✅ 已完成 |

---

## Phase 6：多数据源优先级链 + TickFlow 深度接入

### 6.0 设计理念

建立**多数据源优先级链 (Data Source Chain)** 机制，对每个数据类别（标的列表、K线、实时行情）定义有序的数据源队列。请求时从最高优先级源开始尝试，若失败则自动降级到下一级，以最大程度确保**数据可用性与质量**。

#### 优先级链设计

| 数据类别 | A股/ETF 优先级链 | 虚拟货币优先级链 |
|----------|------------------|-----------------|
| 标的列表 | TickFlow Universe → AKShare → BaoStock | Binance exchangeInfo → OKX |
| 历史K线(日线) | TickFlow `/v1/klines` → Tushare → AKShare → BaoStock → Efinance | Binance → OKX |
| 分钟K线 | TickFlow `/v1/klines` → Tushare → AKShare | Binance → OKX |
| 日内分时 | TickFlow `/v1/klines/intraday` → AKShare | Binance → OKX |
| 实时行情(REST) | TickFlow `/v1/quotes` → AKShare → Efinance | Binance 24hr → OKX |
| 实时行情(推送) | TickFlow WebSocket → 轮询 fallback | Binance WebSocket → OKX WebSocket |
| 五档行情 | TickFlow `/v1/depth` (付费) → 不可用 | Binance depth → OKX |
| 财务数据 | TickFlow financials (付费) → Tushare → AKShare | N/A |

> **核心原则**: TickFlow 为付费源，响应速度快、数据质量高，作为 A股/ETF 的首选；免费源作为兜底保障。

### 6.1 TickFlow API 接入摘要

基于 [TickFlow 文档](https://docs.tickflow.org/zh-Hans) 整理：

#### 服务端点
| 环境 | Base URL | 说明 |
|------|----------|------|
| 完整服务 | `https://api.tickflow.org` | 需 API Key，实时行情+分钟K线 |
| 免费服务 | `https://free-api.tickflow.org` | 无需 Key，仅日K+标的信息 |

#### 认证方式
- Header: `x-api-key: YOUR_API_KEY`
- WebSocket: `wss://api.tickflow.org/v1/ws/stream?api_key=YOUR_API_KEY`
- Python SDK: `pip install "tickflow[all]"` → `TickFlow(api_key="...")` / `TickFlow.free()`

#### 标的代码格式
TickFlow 使用 `代码.交易所后缀` 格式（如 `600519.SH`, `000001.SZ`, `AAPL.US`, `00700.HK`），需要在 Gateway 层做代码转换：
- 内部6位码 `600519` ↔ TickFlow `600519.SH`
- 内部 `HK00700` ↔ TickFlow `00700.HK`
- 美股直接映射: `AAPL` ↔ `AAPL.US`

#### 核心 REST API

| API | 方法 | 说明 | 付费 |
|-----|------|------|------|
| `/v1/quotes` | GET/POST | 实时行情（按 symbols 或 universes） | 需 Key |
| `/v1/depth` | GET | 五档盘口 | Pro/Expert |
| `/v1/klines` | GET | 历史K线（1m~1Y，max 10000条） | 分钟线需 Key |
| `/v1/klines/batch` | GET | 批量K线 | 同上 |
| `/v1/klines/intraday` | GET | 当日分钟K线 | 需 Key |
| `/v1/instruments` | GET/POST | 标的元数据 | 免费 |
| `/v1/universes` | GET | 标的池列表 | 免费 |
| `/v1/universes/{id}` | GET | 标的池详情（含全部代码） | 免费 |
| `/v1/exchanges` | GET | 交易所列表 | 免费 |
| `/v1/financials/*` | GET | 财务数据（利润表/资产负债表等） | Expert |

#### K线响应格式 (列式紧凑)
```json
{
  "data": {
    "timestamp": [1775145600000, ...],
    "open": [10.25, ...],
    "high": [10.25, ...],
    "low": [10.08, ...],
    "close": [10.12, ...],
    "volume": [411518, ...],
    "amount": [417211984.0, ...]
  }
}
```
> 注意：时间戳为**毫秒**级。K线周期: `1m, 5m, 10m, 15m, 30m, 60m, 1d, 1w, 1M, 1Q, 1Y`。
> 复权类型: `forward`(默认), `backward`, `forward_additive`(同东方财富), `backward_additive`, `none`。

#### 实时行情响应
```json
{
  "data": [{
    "symbol": "600000.SH",
    "region": "CN",
    "last_price": 9.72,
    "prev_close": 9.78,
    "open": 9.78,
    "high": 9.78,
    "low": 9.68,
    "volume": 426585,
    "amount": 422430500,
    "timestamp": 1776754802000,
    "ext": {
      "type": "cn_equity",
      "name": "浦发银行",
      "change_pct": -0.006135,
      "change_amount": -0.06,
      "amplitude": 0.010225,
      "turnover_rate": 0.001281
    }
  }]
}
```
> `change_pct` 为比例值（如 -0.006135 即 -0.61%），前端需 *100 转为百分比。

#### WebSocket 实时推送 (付费)
```
连接: wss://api.tickflow.org/v1/ws/stream?api_key=YOUR_API_KEY
订阅: {"op": "subscribe", "channel": "quotes", "symbols": ["600519.SH"]}
推送: {"op": "quotes", "data": [{ ... 同 REST 格式 ... }]}
退订: {"op": "unsubscribe", "channel": "quotes", "symbols": ["600519.SH"]}
```
- 频道: `quotes`(行情) / `depth`(五档盘口)
- 连接保活: 服务端30秒Ping，客户端需回Pong
- 断线需重新 subscribe

#### 标的池 (Universe)
| ID | 说明 |
|----|------|
| `CN_Equity_A` | 沪深 A 股（~5500只） |
| `CN_ETF` | 沪深 ETF（~1400只） |
| `CN_Index` | 沪深指数 |
| `US_Equity` | 美股 |
| `HK_Equity` | 港股 |

#### Python SDK 用法摘要
```python
from tickflow import TickFlow, AsyncTickFlow

# 同步
tf = TickFlow(api_key="xxx")
df = tf.klines.get("600519.SH", period="1d", count=1000, as_dataframe=True)
quotes = tf.quotes.get(symbols=["600519.SH", "000001.SZ"])
universe = tf.universes.get("CN_Equity_A")  # 获取全部A股代码

# 异步
async with AsyncTickFlow(api_key="xxx") as tf:
    df = await tf.klines.get("600519.SH", as_dataframe=True)

# WebSocket
stream = tf.stream
@stream.on_quotes
def on_quotes(quotes): ...
stream.subscribe("quotes", ["600519.SH"])
stream.connect(block=False)  # 非阻塞后台线程

# 异常层级: TickFlowError > APIError > AuthenticationError/RateLimitError/...
# 自动重试: 内置指数退避，可配置 max_retries / timeout
```

### 6.2 后端：数据源链管理器

新建文件：`backend/src/services/data_source_chain.py`

```python
class DataSourceChain:
    """数据源优先级链管理器"""

    def __init__(self, config: dict):
        self._chains = {}  # {category: [source1, source2, ...]}
        self._health = {}  # {source_name: {healthy: bool, last_fail_at, fail_count}}

    def register_chain(self, category: str, sources: list[DataSourceAdapter]):
        """注册某数据类别的优先级链"""

    async def fetch(self, category: str, **kwargs) -> Any:
        """按优先级链依次尝试，成功即返回，全部失败则抛异常"""
        for source in self._chains[category]:
            if not self._is_healthy(source):
                continue  # 跳过近期失败的源
            try:
                result = await source.fetch(**kwargs)
                self._mark_success(source)
                return result
            except Exception as e:
                self._mark_failure(source, e)
                logger.warning(f"[DataSourceChain] {source.name} 失败: {e}, 尝试下一个")
        raise AllSourcesFailedError(category)

    def _is_healthy(self, source) -> bool:
        """指数退避: 失败N次后冷却 min(2^N, 300) 秒"""

    def _mark_failure(self, source, error):
        """记录失败并判断是否为权限/配额错误（永久跳过 vs 临时退避）"""
```

### 6.3 后端：扩展 TickFlowFetcher

在现有 `backend/data_provider/tickflow_fetcher.py` 基础上扩展，补全 P1 接口：

```python
class TickFlowFetcher(BaseFetcher):
    """TickFlow 数据获取器 — 完整版"""

    # --- 新增标的列表接口 ---
    def get_symbol_list(self, market_type: str) -> list[dict]:
        """通过 Universe 获取标的列表"""
        universe_map = {
            'cn_stock': 'CN_Equity_A',
            'cn_etf': 'CN_ETF',
            'cn_index': 'CN_Index',
            'us_stock': 'US_Equity',
            'hk_stock': 'HK_Equity',
        }
        universe = tf.universes.get(universe_map[market_type])
        instruments = tf.instruments.batch(symbols=universe['symbols'])
        return [self._normalize_instrument(inst) for inst in instruments]

    # --- 新增K线接口 ---
    def get_klines(self, symbol, period, count, start_time, end_time, adjust) -> dict:
        """获取K线数据，返回统一格式"""
        tf_symbol = self._to_tickflow_symbol(symbol)
        data = tf.klines.get(tf_symbol, period=period, count=count,
                             start_time=start_time, end_time=end_time,
                             adjust=adjust or 'forward')
        return self._normalize_klines(data)

    # --- 新增实时行情接口 ---
    def get_realtime_quotes(self, symbols: list[str]) -> list[dict]:
        """批量获取实时行情"""
        tf_symbols = [self._to_tickflow_symbol(s) for s in symbols]
        quotes = tf.quotes.get(symbols=tf_symbols)
        return [self._normalize_quote(q) for q in quotes]

    # --- 代码转换 ---
    @staticmethod
    def _to_tickflow_symbol(code: str) -> str:
        """内部代码 → TickFlow 格式"""
        # 600xxx/601xxx/603xxx/688xxx → xxx.SH
        # 000xxx/002xxx/003xxx/300xxx → xxx.SZ
        # 92xxxx/43xxxx/8xxxxx → xxx.BJ
        # HK00700 → 00700.HK
        # AAPL → AAPL.US

    @staticmethod
    def _from_tickflow_symbol(tf_symbol: str) -> str:
        """TickFlow 格式 → 内部代码"""
```

### 6.4 后端：改造 MarketGateway 使用数据源链

修改 `backend/src/services/market_gateway.py`：

```python
class MarketGateway:
    def __init__(self):
        self._cache = MarketCache()
        self._chain = DataSourceChain()

        # 注册标的列表链
        self._chain.register('symbols:cn_stock',
            [TickFlowSymbolSource(), AKShareSymbolSource()])
        self._chain.register('symbols:cn_etf',
            [TickFlowSymbolSource(), AKShareSymbolSource()])
        self._chain.register('symbols:crypto',
            [BinanceSymbolSource(), OKXSymbolSource()])

        # 注册K线链
        self._chain.register('kline:cn',
            [TickFlowKlineSource(), TushareKlineSource(),
             AKShareKlineSource(), BaostockKlineSource(), EfinanceKlineSource()])
        self._chain.register('kline:crypto',
            [BinanceKlineSource(), OKXKlineSource()])

        # 注册实时行情链
        self._chain.register('realtime:cn',
            [TickFlowRealtimeSource(), AKShareRealtimeSource(), EfinanceRealtimeSource()])
        self._chain.register('realtime:crypto',
            [BinanceRealtimeSource(), OKXRealtimeSource()])
```

### 6.5 后端：配置管理

在 `backend/src/config.py` 中添加数据源配置：

```python
# TickFlow 配置
TICKFLOW_API_KEY = os.environ.get('TICKFLOW_API_KEY', '')
TICKFLOW_BASE_URL = os.environ.get('TICKFLOW_BASE_URL', 'https://api.tickflow.org')
TICKFLOW_FREE_URL = 'https://free-api.tickflow.org'
TICKFLOW_TIMEOUT = 30.0
TICKFLOW_WEBSOCKET_ENABLED = True  # 是否启用 WebSocket 推送

# 数据源优先级（可通过配置覆盖默认值）
DATA_SOURCE_PRIORITY = {
    'cn_kline': ['tickflow', 'tushare', 'akshare', 'baostock', 'efinance'],
    'cn_realtime': ['tickflow', 'akshare', 'efinance'],
    'cn_symbols': ['tickflow', 'akshare'],
    'crypto_kline': ['binance', 'okx'],
    'crypto_realtime': ['binance', 'okx'],
}
```

### 6.6 前端：设置页面 TickFlow API Key 配置

修改 `src/renderer/src/Settings.vue`（设置页面）：

- 新增「数据源配置」区域
- TickFlow API Key 输入框（密码型，带测试连接按钮）
- Tushare Token 输入框（已有，可合并展示）
- 数据源优先级排序（高级设置，可拖拽调整顺序）
- 配置保存后通过 IPC 通知后端重载

### 6.7 实现步骤

| 步骤 | 内容 | 文件 |
|------|------|------|
| 6.7.1 | TickFlow 代码转换工具 | `market_gateway.py` 新增 `_to_tickflow_symbol()` / `_from_tickflow_symbol()` | ✅ 已完成 |
| 6.7.2 | 扩展 TickFlowFetcher (标的列表、K线、实时行情) | `data_provider/tickflow_fetcher.py` | ✅ 已完成 |
| 6.7.3 | DataSourceChain 数据源链管理器 | `src/services/data_source_chain.py` (新建) | ✅ 已完成 |
| 6.7.4 | MarketGateway 改造为数据源链模式 | `src/services/market_gateway.py` | ✅ 已完成 |
| 6.7.5 | 配置管理 (API Key + 优先级) | `src/config.py` + Settings UI | ✅ 已完成 |
| 6.7.6 | 集成测试：TickFlow ↔ AKShare 自动降级 | 验证 API Key 无效/超限时自动切换 | ✅ 已完成 (20 tests) |
| 6.7.7 | 删除旧缓存、重建含 TickFlow 数据 | `market_cache.db` 重建 | ✅ 自动处理 |

---

## Phase 7：WebSocket 实时推送 + 五档行情

### 7.1 后端 WebSocket 服务

新建文件：`backend/src/services/realtime_ws.py`

- 后端作为 TickFlow WebSocket 的**中继代理**：
  - 后端连接 `wss://api.tickflow.org/v1/ws/stream`
  - 前端通过本地 WebSocket `ws://127.0.0.1:8100/ws/stream` 订阅
  - 好处：API Key 不暴露给前端，多个前端页面共享一个上游连接
- 支持频道：`quotes` (行情) + `depth` (五档)
- 自动重连 + 订阅恢复

### 7.2 前端 WebSocket 消费

修改 `SymbolBrowser.vue` + `SymbolList.vue`：
- 连接本地 WS 订阅当前可见标的
- 替代 REST 轮询，降低延迟到亚秒级
- 五档行情在标的详情弹窗中展示

### 7.3 TradingView DataFeed 实时推送

修改 `src/renderer/src/service/dataSource/unified/datafeed.ts`：
- `subscribeBars()`: 通过本地 WS 订阅，推送新 bar
- A股盘中实时更新当前 bar (分钟级)

---

## Phase 8：港股 / 美股市场接入 + 财务数据

### 8.1 港股/美股标的列表与K线

- TickFlow 已支持 `US_Equity` / `HK_Equity` 标的池
- K线: 日线/周线/月线（美股/港股暂无分钟K线）
- 实时行情: REST + WebSocket 均支持
- 启用 `MARKET_TYPES` 中 `hk_stock` 和 `us_stock`

### 8.2 财务数据接口

TickFlow 提供（Expert 套餐）：
- `tf.financials.income()` — 利润表
- `tf.financials.balance_sheet()` — 资产负债表
- `tf.financials.cash_flow()` — 现金流量表
- `tf.financials.metrics()` — 核心财务指标（EPS、ROE、营收增长等）
- `tf.financials.shares()` — 股本表

新建 API 端点：
```
GET /api/v1/market/financials?symbol=600519&type=income
GET /api/v1/market/financials?symbol=600519&type=balance
GET /api/v1/market/financials?symbol=600519&type=metrics
```

### 8.3 前端：标的详情面板

在 SymbolBrowser 中新增侧边栏/弹窗式标的详情：
- 基本信息（代码、名称、上市日期、所属行业）
- 实时行情（最新价、涨跌、成交量）
- 五档行情（买卖盘口）
- 核心财务指标（PE、PB、ROE、营收增长率）

---

## 六、文件变更清单（预估）

### 新增文件
```
backend/
├─ api/v1/endpoints/market.py          # 市场数据 API ✅ 已完成
├─ api/v1/schemas/market.py            # 数据模型定义 ✅ 已完成
├─ src/services/market_cache.py        # 缓存服务 ✅ 已完成
├─ src/services/market_gateway.py      # 数据网关服务 ✅ 已完成
├─ src/services/data_source_chain.py   # 数据源优先级链管理器 (Phase 6 新增)
├─ src/services/realtime_ws.py         # WebSocket 实时推送中继 (Phase 7 新增)
└─ data/market_cache.db                # SQLite 缓存数据库 ✅ 已完成

src/renderer/
├─ symbol-browser.html                 # 标的浏览器入口 ✅ 已完成
├─ src/symbol-browser.js               # Vue 挂载 ✅ 已完成
├─ src/SymbolBrowser.vue               # 主组件 ✅ 已完成
├─ src/components/MarketTypeSelector.vue  # ✅ 已完成
├─ src/components/SymbolSearchBar.vue     # ✅ 已完成 (含拼音搜索/历史记录)
├─ src/components/SymbolList.vue          # ✅ 已完成 (含拖拽排序/行情显示)
├─ src/components/SymbolContextMenu.vue   # ✅ 已完成
└─ src/service/
   ├─ marketDataService.ts             # 统一数据服务 ✅ 已完成
   └─ dataSource/unified/
      └─ datafeed.ts                   # 统一 TradingView DataFeed ✅ 已完成
```

### 修改文件
```
src/main/index.js                      # 添加固定标签页逻辑 ✅
src/renderer/src/index.js              # 交易模式标签管理 ✅
src/renderer/src/Chart.vue             # 支持 symbol 参数 ✅
src/renderer/src/Chart.vue              # 多数据源 DataFeed 切换 ✅
src/preload/index.js                   # 新增 IPC 通道 ✅
backend/api/v1/__init__.py             # 注册新路由 ✅
electron.vite.config.mjs               # 新增页面入口 ✅
```

---

## 七、风险与注意事项

1. **AKShare 反爬**：已有节流与退避机制，标的列表接口调用频率低，风险可控
2. **数据一致性**：不同数据源的 K 线时间对齐（交易时段、时区）需统一处理
3. **性能**：A股 5000+ 标的，需虚拟列表 + 搜索索引，避免卡顿
4. **后端启动**：标的浏览器依赖后端服务，需处理后端未启动时的 graceful fallback
5. **数据源切换**：从原来前端直连 Binance 切换到统一层时，确保虚拟货币体验不降级
6. **TickFlow API Key 安全**：Key 仅存于后端，WebSocket 通过后端中继转发，前端永远不持有 Key
7. **付费配额管理**：TickFlow 按套餐有不同请求限额，需监控用量并在 `RateLimitError` 时自动降级到免费源
8. **代码格式兼容**：TickFlow 使用 `.SH/.SZ/.BJ/.US/.HK` 后缀，现有系统使用纯数字码，转换层需全面覆盖北交所、科创板等新市场
9. **WebSocket 稳定性**：TickFlow WS 30秒 Ping/Pong，断线需重连+重新订阅，后端中继需完善心跳与重连机制
10. **多源数据差异**：不同源的价格精度、复权算法、成交量单位可能不同，归一化层需严格对齐