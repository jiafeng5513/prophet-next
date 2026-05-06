# 市场级批量下载缓存 - 开发计划

## 一、需求概述

将本地缓存时间轴改为视频编辑软件风格：每个市场（加密Binance、加密OKX、A股、港股、美股）分别占一条轨道，用户在时间轴上划定时间范围后，一键下载该市场的**全部品种**数据。

### 关键约束

- 用户典型使用场景：下载 1~2 年跨度数据
- 不需要支持 10 年全量历史（极端场景不考虑）

### 下载耗时估算（1 年日线）

| 市场 | 品种数 | 每品种请求数 | 总请求 | 预估耗时 |
|------|--------|-------------|--------|----------|
| 加密(Binance) | ~600 | 1 | ~600 | **~5 分钟** |
| 加密(OKX) | ~400 | 1-2 | ~600 | **~5 分钟** |
| A股 | ~5000 | 1 | ~5000 | **30~60 分钟** |
| 港股 | ~2500 | 1 | ~2500 | **15~30 分钟** |
| 美股 | ~8000 | 1 | ~8000 | **40~80 分钟** |

> 注：以上基于 DownloadEngine 500ms 间隔 + 数据源自身限流计算，3 并发。实际耗时可接受。

---

## 二、现有基础

| 组件 | 状态 | 需改造 |
|------|------|--------|
| 多轨道时间轴 Canvas UI | ✅ 已有 | 小改：去掉品种输入，改为市场级操作 |
| 框选时间范围交互 | ✅ 已有 | 不变 |
| `POST /api/v1/cache/download` | ✅ 单品种 | 新增批量端点 |
| `DownloadEngine` | ✅ 已有 | 增加批量任务展开 + 聚合进度 |
| `KlineCacheManager` | ✅ 已有 | 增加批量任务管理 |
| 品种列表接口 | ❌ 缺失 | **新增** |

---

## 三、技术方案

### 3.1 品种列表发现层

新建 `backend/src/services/symbol_list_service.py`，统一各市场品种列表获取：

```python
class SymbolListService:
    """统一品种发现服务"""
    
    async def get_symbols(self, market: str) -> List[Dict[str, str]]:
        """返回 [{"symbol": "BTCUSDT", "name": "BTC/USDT"}, ...]"""
        
    # 各市场实现：
    # crypto_binance: GET https://api.binance.com/api/v3/exchangeInfo → 筛选 TRADING 状态的 USDT 交易对
    # crypto_okx:     GET https://www.okx.com/api/v5/public/instruments?instType=SPOT → 筛选活跃交易对
    # cn:             调用 TushareFetcher.get_stock_list() 或 BaostockFetcher.get_stock_list()
    # us:             调用 TickFlowFetcher.get_symbol_list("us_stock") 或 YfinanceFetcher
    # hk:             调用 TickFlowFetcher.get_symbol_list("hk_stock") 或 LongbridgeFetcher
```

### 3.2 批量下载 API

新增端点 `POST /api/v1/cache/download/market`：

```python
class MarketDownloadRequest(BaseModel):
    market: str               # "crypto_binance", "crypto_okx", "cn", "us", "hk"
    interval: str = "1d"
    start_time: int           # Unix 毫秒
    end_time: int

class MarketDownloadResponse(BaseModel):
    batch_id: str             # 批次ID
    total_symbols: int        # 总品种数
    tasks_created: int        # 创建的子任务数
    message: str
```

**流程：**
1. 调用 `SymbolListService.get_symbols(market)` 获取品种列表
2. 为每个品种创建子任务（复用现有 `create_download_task`）
3. 记录批次 ID → 子任务映射
4. 返回批次 ID + 总品种数

### 3.3 批次进度聚合

新增端点 `GET /api/v1/cache/download/batch/{batch_id}/progress`：

```python
class BatchProgressResponse(BaseModel):
    batch_id: str
    market: str
    total_symbols: int
    completed_symbols: int
    failed_symbols: int
    overall_progress: float   # 0.0 ~ 1.0
    status: str               # "running", "completed", "partial_failed"
    current_tasks: List[dict] # 当前正在执行的子任务详情
```

### 3.4 前端时间轴改造

修改 `CacheTimeline.vue`：

| 改动点 | 说明 |
|--------|------|
| 去掉手动输入品种 | 框选/日期选择后直接按市场下载全部 |
| 下载按钮语义变更 | "下载选中范围" → "下载 {市场名} 全部品种 ({日期范围})" |
| 进度面板升级 | 显示批次级进度（如 "A股：234/5012 品种 (4.7%)"） |
| 增加品种数预览 | 框选后显示 "将下载 ~600 个品种"，用户确认后执行 |
| 支持取消整个批次 | 取消按钮一键取消批次内所有子任务 |

### 3.5 架构图

```
前端 CacheTimeline.vue
  │ 框选时间 + 点击"下载"
  ▼
POST /api/v1/cache/download/market
  │ { market: "crypto_binance", interval: "1d", start_time, end_time }
  ▼
SymbolListService.get_symbols("crypto_binance")
  │ → ["BTCUSDT", "ETHUSDT", "BNBUSDT", ... ~600个]
  ▼
为每个品种创建下载子任务 → KlineCacheManager._download_tasks
  │ 返回 batch_id
  ▼
DownloadEngine._poll_loop() 
  │ 按并发3逐个执行（现有逻辑不变）
  ▼
前端轮询 GET /api/v1/cache/download/batch/{batch_id}/progress
  │ → { completed: 234, total: 600, progress: 0.39 }
  ▼
进度条实时更新
```

---

## 四、开发阶段

### Phase 1: 品种列表服务（后端）

- [ ] 创建 `backend/src/services/symbol_list_service.py`
- [ ] 实现 `crypto_binance` 品种列表：调 Binance exchangeInfo API
- [ ] 实现 `crypto_okx` 品种列表：调 OKX instruments API
- [ ] 实现 `cn` 品种列表：复用 TushareFetcher/BaostockFetcher 的 get_stock_list
- [ ] 实现 `us` 品种列表：复用 TickFlowFetcher.get_symbol_list("us_stock")
- [ ] 实现 `hk` 品种列表：复用 TickFlowFetcher.get_symbol_list("hk_stock")
- [ ] 品种列表缓存：内存缓存 + TTL（避免频繁调接口，有效期 1 小时）
- [ ] 新增 API `GET /api/v1/cache/symbols/{market}` 供前端预览品种数

### Phase 2: 批量下载引擎（后端）

- [ ] `KlineCacheManager` 新增批次管理：
  - `create_batch_download(market, interval, start_time, end_time, symbols)` → batch_id
  - `get_batch_progress(batch_id)` → 聚合进度
  - `cancel_batch(batch_id)` → 取消所有子任务
- [ ] 新增 API `POST /api/v1/cache/download/market` — 批量下载入口
- [ ] 新增 API `GET /api/v1/cache/download/batch/{batch_id}/progress` — 批次进度
- [ ] 新增 API `POST /api/v1/cache/download/batch/{batch_id}/cancel` — 取消批次
- [ ] `DownloadEngine` 调整：批量任务优先级排队（避免一次性 5000 个 pending 堆积）
  - 采用分批释放策略：每次向队列中放入 50 个子任务，完成后再放下一批

### Phase 3: 前端时间轴改造

- [ ] 去掉手动下载面板中的"品种"输入框
- [ ] 框选 / 日期选择后显示预估信息：
  - 调 `GET /api/v1/cache/symbols/{market}` 获取品种数
  - 显示 "将下载 加密(Binance) 全部 ~600 个品种，1d 日线，2025-01-01 ~ 2026-01-01"
- [ ] 确认下载后调 `POST /api/v1/cache/download/market`
- [ ] 进度面板改为批次级显示：
  - 整体进度条 + 百分比
  - 已完成/总数 品种计数
  - 当前正在下载的品种列表（最多显示 3 个）
  - 预估剩余时间（基于已完成速率）
- [ ] 批次取消按钮

### Phase 4: 品种列表管理（可选增强）

- [ ] 前端品种列表预览弹窗：点击查看该市场全部品种
- [ ] 支持品种过滤/排除：用户可取消不想下载的品种
- [ ] 支持"仅下载指数+ETF"快捷选项（针对A股/美股品种数过多场景）
- [ ] 品种列表刷新按钮

### Phase 5: 测试

- [ ] SymbolListService 单元测试：Mock 各交易所 API 响应
- [ ] 批量下载流程集成测试：创建批次 → 进度更新 → 完成/取消
- [ ] 前端E2E：框选 → 确认 → 进度展示 → 完成刷新时间轴
- [ ] 边界条件：品种列表为空、下载中途网络断开、部分品种失败

---

## 五、文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/src/services/symbol_list_service.py` | 品种列表发现服务 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/api/v1/endpoints/cache.py` | 新增 3 个端点（批量下载/批次进度/批次取消/品种列表） |
| `backend/src/services/kline_cache_manager.py` | 新增批次管理方法 |
| `backend/src/services/download_engine.py` | 分批释放策略（防止大量 pending 堆积） |
| `src/renderer/src/components/cache-timeline/CacheTimeline.vue` | 去掉品种输入，改为市场级下载 + 批次进度 |

---

## 六、注意事项

1. **品种列表缓存策略**：避免每次框选都调交易所 API，内存缓存 1 小时 TTL
2. **分批释放**：A股 5000 品种不应一次性创建 5000 个 pending task，而是分批 50 个释放
3. **失败容忍**：部分品种下载失败不应影响整个批次，记录失败列表供后续重试
4. **可中断**：用户可随时取消，已下载的数据保留
5. **幂等性**：重复下载同一品种同一范围应跳过已有缓存段（复用现有缺口分析逻辑）
6. **磁盘空间**：大量品种下载可能占用较多磁盘，在确认弹窗中显示预估大小
