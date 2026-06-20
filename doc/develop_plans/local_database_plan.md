# 行情数据源优化与本地缓存管理 - 开发计划

## 一、需求概述

1. 将 Binance 和 OKX 加入行情数据渠道列表（支持 API Key 认证）
2. 添加本地缓存管理功能，通过视频编辑器风格的时间轴 UI 展示各市场缓存状态
3. 支持在时间轴上操作：主动下载/删除指定时间段的缓存数据
4. 访问行情数据时优先使用本地缓存
5. 不同数据源的历史行情（REST）与实时行情（WebSocket）接口分离管理

---

## 二、现有架构分析

### 2.1 数据获取层

| 组件 | 说明 |
|------|------|
| `BaseFetcher` | 抽象基类，定义 `_fetch_raw_data` / `_normalize_data` 模板方法 |
| `DataFetcherManager` | 按优先级管理多个 Fetcher，支持故障转移 |
| `CircuitBreaker` | 熔断器，连续失败 3 次自动切换 |
| `TickFlowFetcher` | 已有 WebSocket + REST 分离设计的参考实现 |

### 2.2 已有缓存机制

- `backend/data/cache/market_cache.db` — SQLite WAL 模式（市场数据缓存）
- 内存缓存：`_fundamental_cache`（基本面，TTL + LRU）
- 前端缓存：`marketDataService.ts`（symbols/marketTypes 内存 TTL 缓存）

### 2.3 前端设置页面

- `Settings.vue` 中 `dataSourcePresets` 定义渠道卡片
- 支持拖拽排序（SortableJS）、启用/禁用、凭据展开编辑
- 分组显示：行情数据源渠道 / 新闻搜索源渠道 / 参数开关

---

## 三、API 接口调研

### 3.1 Binance

| 用途 | 接口 | 说明 |
|------|------|------|
| 历史K线 | `GET /api/v3/klines` | 参数: symbol, interval, startTime, endTime, limit(max 1000) |
| 实时K线 | WebSocket `<symbol>@kline_<interval>` | 推送间隔 1s~2s，支持 1s/1m/5m/15m/1h/4h/1d/1w/1M |
| 24h行情 | WebSocket `<symbol>@ticker` | 24h 滚动窗口统计 |
| 聚合成交 | WebSocket `<symbol>@aggTrade` | 实时逐笔成交 |

**关键信息**：
- Base URL: `https://api.binance.com`（市场数据可用 `https://data-api.binance.vision` 无需鉴权）
- WebSocket: `wss://stream.binance.com:9443/ws/<streamName>`
- K线间隔: 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
- 单次最多返回 1000 条K线，需分页获取历史数据
- WebSocket 单连接有效期 24h，需重连机制
- 市场数据接口无需 API Key（公开接口），但有 IP 速率限制（1200次/分钟）

### 3.2 OKX

| 用途 | 接口 | 说明 |
|------|------|------|
| 近期K线 | `GET /api/v5/market/candles` | 最近 1440 条，参数: instId, bar, after, before, limit(max 300) |
| 历史K线 | `GET /api/v5/market/history-candles` | 更早期数据，参数同上 |
| 实时K线 | WebSocket 订阅 `candle<period>` channel | 频道: candle1m/candle5m/candle1H/candle1D 等 |
| 行情快照 | `GET /api/v5/market/ticker` | 最新价/涨跌幅 |
| 实时行情 | WebSocket 订阅 `tickers` channel | 推送最新价/量 |

**关键信息**：
- REST Base URL: `https://www.okx.com`
- WebSocket (公开): `wss://ws.okx.com:8443/ws/v5/public`
- K线周期: 1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 1W, 1M, 3M
- 每次最多返回 300 条，使用 `after` 参数翻页
- 市场数据接口无需 API Key，但有速率限制（20次/2s per instrument）
- 需注意交易对命名格式：`BTC-USDT`（与 Binance 的 `BTCUSDT` 不同）

### 3.3 TickFlow（已有实现参考）

- REST: 通过 `_client` 获取主指数、市场宽度等
- WebSocket: 内部客户端管理长连接生命周期
- 特点：独立于日线 K 线流程，仅用于市场综述

---

## 四、技术方案设计

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                         │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ 数据源渠道配置    │  │ 缓存时间轴 UI (Canvas/SVG)       │ │
│  │ + Binance/OKX    │  │ - 多轨道（市场维度）              │ │
│  │   渠道卡片       │  │ - 缩放/平移                      │ │
│  └──────────────────┘  │ - 框选下载/删除操作              │ │
│                         └──────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Backend API (FastAPI)                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Cache API │  │ Data Fetcher │  │ WebSocket Manager     │ │
│  │ /cache/* │  │  Manager     │  │ (Binance/OKX/TF)      │ │
│  └─────┬────┘  └──────┬───────┘  └───────────┬───────────┘ │
│        │               │                       │             │
│  ┌─────▼───────────────▼───────────────────────▼───────────┐ │
│  │              CacheManager (SQLite)                        │ │
│  │  - 缓存读写        - 元数据索引        - 完整性标记      │ │
│  └──────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Storage Layer                              │
│  market_cache.db (SQLite WAL)                                │
│  - kline_data 表: 按 (source, symbol, interval, timestamp)   │
│  - cache_meta 表: 按 (market, symbol, interval) 记录覆盖范围 │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 数据库 Schema 设计

```sql
-- K线数据主表
CREATE TABLE IF NOT EXISTS kline_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,          -- 'crypto_binance', 'crypto_okx', 'cn', 'us', 'hk'
    symbol TEXT NOT NULL,          -- 'BTCUSDT', '600519', 'AAPL'
    interval TEXT NOT NULL,        -- '1d', '1h', '5m' 等
    timestamp INTEGER NOT NULL,   -- Unix 毫秒时间戳
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL,
    amount REAL,
    source TEXT,                   -- 数据来源标记
    is_complete BOOLEAN DEFAULT 1, -- 数据是否完整（实时推送的未收盘K线=0）
    created_at INTEGER DEFAULT (strftime('%s','now') * 1000),
    UNIQUE(market, symbol, interval, timestamp)
);

CREATE INDEX idx_kline_lookup ON kline_data(market, symbol, interval, timestamp);
CREATE INDEX idx_kline_market_time ON kline_data(market, interval, timestamp);

-- 缓存元数据表（记录每个品种已缓存的时间范围）
CREATE TABLE IF NOT EXISTS cache_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    start_time INTEGER NOT NULL,   -- 该段缓存起始时间
    end_time INTEGER NOT NULL,     -- 该段缓存结束时间
    completeness REAL DEFAULT 1.0, -- 完整度 0.0~1.0（中间可能有空洞）
    record_count INTEGER DEFAULT 0,
    source TEXT,
    updated_at INTEGER DEFAULT (strftime('%s','now') * 1000),
    UNIQUE(market, symbol, interval, start_time)
);

CREATE INDEX idx_meta_lookup ON cache_meta(market, symbol, interval);
```

### 4.3 缓存优先访问策略

```
用户请求 get_daily_data(symbol, start, end)
    │
    ▼
CacheManager.query(symbol, interval, start, end)
    │
    ├─ 完全命中 → 直接返回缓存数据
    │
    ├─ 部分命中 → 识别缺失区间
    │       │
    │       ▼
    │   Fetcher 获取缺失部分 → 写入缓存 → 拼接返回
    │
    └─ 完全未命中 → Fetcher 获取全部 → 写入缓存 → 返回
```

### 4.4 WebSocket 实时数据管理

```
┌───────────────────────────────────────────┐
│         RealtimeWSManager                  │
│                                            │
│  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Binance WS  │  │  OKX WS             │ │
│  │ Client      │  │  Client             │ │
│  │             │  │                     │ │
│  │ kline stream│  │  candle channel     │ │
│  │ ticker      │  │  tickers channel    │ │
│  └──────┬──────┘  └──────────┬──────────┘ │
│         │                     │            │
│         ▼                     ▼            │
│  ┌─────────────────────────────────────┐  │
│  │   统一消息处理 & 写入 CacheManager   │  │
│  │   (未收盘K线 is_complete=0)          │  │
│  └─────────────────────────────────────┘  │
└───────────────────────────────────────────┘
```

---

## 五、开发阶段规划

### Phase 1: Binance & OKX Fetcher 实现（后端） ✅ 已完成

**实际完成日期：2026-05-04**

#### 1.1 BinanceFetcher 实现
- [x] 创建 `backend/data_provider/binance_fetcher.py`
- [x] 继承 `BaseFetcher`，实现 `_fetch_raw_data` 和 `_normalize_data`
- [x] REST 接口封装：`GET /api/v3/klines`，支持自动分页（单次 1000 条限制）
- [x] 交易对格式处理：统一内部格式 ↔ Binance 格式（`BTC-USDT` → `BTCUSDT`）
- [x] 速率限制处理：1200 req/min，添加请求间隔控制
- [x] 错误处理：HTTP 429/418 限流响应处理

#### 1.2 OKXFetcher 实现
- [x] 创建 `backend/data_provider/okx_fetcher.py`
- [x] 继承 `BaseFetcher`，实现 `_fetch_raw_data` 和 `_normalize_data`
- [x] REST 接口封装：`GET /api/v5/market/candles` + `/history-candles`，自动翻页（每次 300 条）
- [x] 交易对格式处理：`BTC-USDT` 格式
- [x] K线周期映射：统一间隔格式 → OKX 格式（`1d` → `1D`, `1h` → `1H`）
- [x] 速率限制处理：20 req/2s per instrument

#### 1.3 WebSocket 实时客户端
- [x] 创建 `backend/data_provider/binance_ws_client.py`
  - 连接管理：自动重连、24h 连接刷新、ping/pong 心跳
  - 订阅管理：`<symbol>@kline_<interval>` 和 `<symbol>@ticker`
  - 消息解析：K 线实时推送 → UnifiedRealtimeQuote
- [x] 创建 `backend/data_provider/okx_ws_client.py`
  - 连接管理：`wss://ws.okx.com:8443/ws/v5/public`，心跳 ping/pong
  - 订阅管理：`candle<period>` 和 `tickers` channel
  - 消息解析：统一格式输出

#### 1.4 注册与配置
- [x] `config.py` 添加 `binance_api_key`, `binance_api_secret`, `okx_api_key`, `okx_secret_key`, `okx_passphrase`
- [x] `__init__.py` 注册新 Fetcher（Binance 优先级 6，OKX 优先级 7）
- [x] 加密货币市场检测函数：`is_crypto_code()`

---

### Phase 2: 本地缓存管理层（后端） ✅ 已完成

**实际完成日期：2026-05-04**

#### 2.1 CacheManager 核心实现
- [x] 创建 `backend/src/services/kline_cache_manager.py`
- [x] SQLite 表创建与迁移（`kline_data` + `kline_cache_meta`）
- [x] 写入接口：批量 upsert K线数据 + 自动更新 cache_meta
- [x] 查询接口：按 (market, symbol, interval, time_range) 查询
- [x] 缺口分析：给定请求范围，返回已缓存段和缺失段列表
- [x] 删除接口：按时间范围删除缓存数据 + 更新 meta
- [x] 合并逻辑：相邻/重叠的 cache_meta 记录自动合并

#### 2.2 缓存集成到 DataFetcherManager
- [x] 修改 `DataFetcherManager.get_daily_data()` 流程：
  1. 先查 CacheManager
  2. 对缺失段调用 Fetcher
  3. 写入缓存后返回完整数据
- [x] 确保线程安全（读写锁分离）
- [x] 支持强制刷新标志（跳过缓存）

#### 2.3 缓存状态查询 API
- [x] `GET /api/v1/cache/status` — 返回各市场缓存概览
- [x] `GET /api/v1/cache/timeline/summary` — 返回时间轴数据
- [x] `POST /api/v1/cache/download` — 触发指定范围的缓存下载任务
- [x] `DELETE /api/v1/cache/range` — 删除指定范围缓存
- [x] `GET /api/v1/cache/download/progress` — 下载任务进度查询
- [x] `POST /api/v1/cache/download/{task_id}/cancel` — 取消下载任务
- [x] `DELETE /api/v1/cache/market/{market}` — 清空指定市场缓存

#### 2.4 后台下载任务引擎
- [x] 创建 `backend/src/services/download_engine.py`
- [x] 异步任务队列：支持多品种并行下载（MAX_CONCURRENT=3）
- [x] 进度上报：轮询返回下载进度
- [x] 断点续传：分片下载，记录进度
- [x] 速率控制：根据数据源限制自动调节下载速度（500ms间隔）
- [x] 注册到 FastAPI lifespan（app.py startup/shutdown）

---

### Phase 3: 缓存时间轴 UI（前端） ✅ 已完成

**实际完成日期：2026-05-04**

#### 3.1 时间轴组件设计
- [x] 创建 `src/renderer/src/components/cache-timeline/CacheTimeline.vue`
- [x] Canvas 2D 渲染引擎
  - 横轴：时间轴，支持缩放（滚轮）和平移（Shift+拖拽）
  - 纵轴：多轨道，每个市场一个轨道（A股/港股/美股/加密）
  - 时间刻度：自适应精度，根据缩放级别显示年/月/日
- [x] 缩放控制：鼠标滚轮缩放 + 自适应

#### 3.2 轨道数据渲染
- [x] 每条轨道显示：
  - 🟢 绿色段：已缓存且完整
  - 🟡 黄色段：已缓存但数据不完全（completeness < 1.0）
  - ⬜ 灰色段：未缓存
- [x] 轨道标签：市场名称
- [x] Hover 提示：显示该段的具体时间范围、记录数

#### 3.3 交互操作
- [x] 框选功能：鼠标拖动选择时间范围
- [x] 操作按钮：
  - "下载选中范围" → 调用 `POST /api/v1/cache/download`
  - "删除选中范围" → 确认后调用 `DELETE /api/v1/cache/range`
- [x] 下载进度：轮询显示下载进度
- [x] 缓存状态摘要显示

#### 3.4 集成到设置页面
- [x] 在 `Settings.vue` 的数据源分组下添加 "💾 本地缓存管理" 区域
- [x] 位置：行情数据渠道卡片列表下方
- [x] 引入 CacheTimeline 组件

---

### Phase 4: 前端数据源配置集成 ✅ 已完成

**实际完成日期：2026-05-04**

#### 4.1 渠道卡片扩展
- [x] `dataSourcePresets` 添加 Binance 和 OKX（含 fields/fieldLabels/optional）
- [x] 渠道卡片 UI 适配：optional 渠道显示 "可选" 标记
- [x] 保存逻辑：映射到后端 `BINANCE_API_KEY` / `OKX_API_KEY` 等配置项
- [x] 动态字段渲染：根据 preset.fields 循环生成输入框

#### 4.2 实时行情源优先级
- [x] `parseDsChannels` 支持 binance/okx 子源映射
- [x] 加密货币品种自动路由到 Binance/OKX（`_detect_market` + crypto routing）

---

### Phase 5: 测试与优化 ✅ 已完成

**实际完成日期：2026-05-04**

#### 5.1 单元测试
- [x] BinanceFetcher: Mock REST 响应，验证数据标准化、交易对转换
- [x] OKXFetcher: Mock REST 响应，验证翻页逻辑、数据标准化
- [x] KlineCacheManager: 缓存写入/查询/幂等性/缺口分析/删除/合并/状态查询/时间轴/任务生命周期
- [x] 缓存集成: 验证 cache-first 策略正确性、市场检测、时间范围解析
- [x] WebSocket 客户端基础测试: 连接创建、订阅追踪

**测试结果：26 项测试全部通过** (`tests/test_crypto_and_cache.py`)

#### 5.2 集成测试
- [x] 缓存命中跳过网络请求验证
- [x] 下载任务生命周期：创建 → 进度更新 → 取消

#### 5.3 性能优化（已内置）
- [x] SQLite 批量写入优化（事务内 batch insert，WAL 模式）
- [x] 缓存查询索引优化（复合索引 market+symbol+interval+timestamp）
- [x] 前端时间轴 Canvas 2D 渲染（避免 DOM 性能问题）
- [x] 下载引擎并发控制（semaphore MAX_CONCURRENT=3）

---

## 六、关键技术决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 缓存存储 | SQLite (WAL模式) | 已有基础设施，单文件部署，读写性能够用 |
| 时间轴渲染 | Canvas 2D | 大量数据点渲染性能优于 SVG/DOM |
| WebSocket 库 | `websockets` (Python) | 异步原生支持，成熟稳定 |
| 下载任务 | asyncio Task Queue | 与现有 FastAPI 异步框架一致 |
| 缓存颗粒度 | 按 K 线间隔存储 | 日线/小时线/分钟线分别缓存 |
| 交易对格式 | 内部统一为 `BASE-QUOTE` | 如 `BTC-USDT`，在各 Fetcher 内部转换 |

---

## 七、文件变更清单

### 新增文件

```
backend/
├── data_provider/
│   ├── binance_fetcher.py          # Binance REST K线获取 ✅
│   ├── binance_ws_client.py        # Binance WebSocket 实时客户端 ✅
│   ├── okx_fetcher.py              # OKX REST K线获取 ✅
│   └── okx_ws_client.py            # OKX WebSocket 实时客户端 ✅
├── src/
│   └── services/
│       ├── kline_cache_manager.py  # 本地缓存管理核心 ✅
│       └── download_engine.py      # 后台下载任务引擎 ✅
├── api/v1/
│   └── endpoints/cache.py         # 缓存管理 API 路由 ✅
├── tests/
│   └── test_crypto_and_cache.py   # 单元测试（26项全通过） ✅

src/renderer/src/
├── components/
│   └── cache-timeline/
│       └── CacheTimeline.vue       # 时间轴主组件（Canvas 2D） ✅
```

### 修改文件

```
backend/
├── data_provider/
│   ├── __init__.py                 # 注册 BinanceFetcher, OKXFetcher ✅
│   └── base.py                     # DataFetcherManager 集成缓存逻辑 ✅
│                                    #   + _try_cache_read, _cache_write_async
│                                    #   + _detect_market, _resolve_time_range
│                                    #   + 加密货币路由（Binance→OKX）
├── src/
│   └── config.py                   # 添加 Binance/OKX 配置项 ✅
├── api/
│   ├── app.py                      # lifespan 注册下载引擎 start/stop ✅
│   └── v1/router.py               # 注册缓存路由 ✅

src/renderer/src/
├── Settings.vue                    # 添加 Binance/OKX 渠道 + 缓存管理区域 ✅
```

---

## 八、开发优先级与依赖关系

```
Phase 1 (Fetcher) ──────┐
                         ├──→ Phase 4 (前端配置) ✅
Phase 2 (CacheManager) ─┤
                         ├──→ Phase 3 (时间轴UI) ✅
                         │
                         └──→ Phase 5 (测试) ✅
```

**全部 5 个阶段已于 2026-05-04 完成开发。**

---

## 九、风险与注意事项

1. **API 限流**：Binance 1200req/min、OKX 20req/2s，需严格控制请求频率，尤其批量下载时
2. **网络环境**：Binance/OKX 在中国大陆可能需要代理，需支持 HTTP/WebSocket proxy 配置
3. **数据一致性**：实时推送的未收盘 K 线需标记 `is_complete=0`，收盘后更新
4. **时区问题**：Binance K线默认 UTC，OKX 默认 UTC，需统一转换处理
5. **磁盘空间**：分钟级缓存数据量较大，需提供缓存大小统计和自动清理策略
6. **WebSocket 生命周期**：Binance 24h 断连、网络波动重连，需健壮的连接管理

---

## 十、项目完成总结

### 完成状态：✅ 全部完成

| 阶段 | 状态 | 核心产出 |
|------|------|----------|
| Phase 1 | ✅ | BinanceFetcher + OKXFetcher + 双平台 WebSocket 客户端 |
| Phase 2 | ✅ | KlineCacheManager + DownloadEngine + Cache REST API |
| Phase 3 | ✅ | CacheTimeline.vue (Canvas 2D 多轨道时间轴) |
| Phase 4 | ✅ | Settings.vue 集成 Binance/OKX 渠道卡片 + 缓存管理区域 |
| Phase 5 | ✅ | 26 项单元测试全通过 + FastAPI lifespan 集成 |

### 待用户验收测试

1. 启动后端，确认 Binance/OKX 数据源可正常获取加密货币K线
2. 验证缓存优先逻辑：首次请求走网络，二次请求命中本地缓存
3. 设置页面验证：Binance/OKX 渠道卡片显示、API Key 保存
4. 缓存时间轴操作：框选时间范围下载/删除数据
5. 下载引擎：触发下载任务后查看进度、取消任务

### 后续可优化方向

- [ ] 大时间范围查询分片 + 流式返回
- [ ] WebSocket 实时K线写入缓存（`is_complete=0`）
- [ ] 缓存自动清理策略（磁盘空间阈值）
- [ ] 时间轴 UI 右键菜单增强
- [ ] 下载任务持久化（重启后恢复未完成任务）