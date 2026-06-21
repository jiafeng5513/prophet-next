# 服务端独立化与客户端-服务端架构改造 — 开发计划

## 一、需求背景

当前 `backend` 与前端（Electron 客户端）一起启动：客户端启动时由主进程
（`client/src/main/index.js` 的 `startFastApiServer`）通过 `uv run uvicorn server:app`
自动拉起后端，二者生命周期绑定。这带来一个核心矛盾：**部分数据需要长期、持续地
采集与归档，服务端应当 7×24 常驻运行**，而客户端会频繁开关。

### 期望达成的效果

1. 客户端启动后能**立即显示标的列表**，尽量减少现场拉取数据。
2. 服务端 **7×24 运行**，持续记录并积攒行情数据到本地数据库；客户端请求某标的
   行情时，尽量命中本地缓存，减少现场拉取。
3. 当前在内网开发测试，使用一台 mac mini（`anna@192.168.50.7`）作为服务端运行。
4. 服务端需要一个**管理功能**：查看服务状态、管理数据缓存、查看客户端连接情况等。
   管理功能通过**客户端内嵌管理面板**提供给授权用户，而非独立的 Web SPA。
5. 未来可能上线乃至商业化，服务端需考虑**客户端鉴权**：不同账号按订阅等级，可用
   的数据、模型等有所不同。
6. Bot 系统（消息推送/通知）后期应迁移到服务端常驻运行，支持多用户订阅与独立推送。

---

## 二、现有架构分析

### 2.1 启动与耦合方式

| 组件 | 现状 |
|------|------|
| Electron 主进程 | `client/src/main/index.js`：`app.whenReady` 时调用 `startFastApiServer()` 自动拉起后端；`window-all-closed`/`before-quit` 时 `stopFastApiServer()` 杀掉后端 |
| 后端入口 | `server/server.py`（`uvicorn server:app`），默认 `0.0.0.0:8100`；`server/main.py` 提供 `--serve-only` / `--schedule` 等模式 |
| FastAPI App | `server/api/app.py`：`create_app()` + `app_lifespan`（已在 lifespan 启动 `download_engine`），挂载 `/ws/market` 实时中继 |

### 2.2 前端如何连接后端（硬编码点）

前端在 **8 处**硬编码 `http://127.0.0.1:8100` / `ws://127.0.0.1:8100`，是解耦的主要改造面：

```
client/src/renderer/src/service/marketDataService.ts   (API_BASE)
client/src/renderer/src/service/realtimeWSClient.ts     (WS_URL)
client/src/renderer/src/Home.vue / SymbolBrowser.vue / MarketBrowser.vue  (API_BASE)
client/src/renderer/src/Backtest.vue / Portfolio.vue    (baseUrl)
client/src/renderer/src/components/cache-timeline/CacheTimeline.vue (baseUrl prop)
```

### 2.3 已有的数据/缓存基础设施（可直接复用）

| 组件 | 说明 |
|------|------|
| `data_provider/*` | Binance/OKX/Akshare/Baostock/Pytdx/TickFlow 等多数据源 Fetcher，含 WS 客户端 |
| `src/services/kline_cache_manager.py` | SQLite K线缓存（`kline_data` + `kline_cache_meta`），缺口分析/合并/删除 |
| `src/services/download_engine.py` | 异步批量下载任务引擎（已注册到 lifespan） |
| `src/services/realtime_ws.py` | `RealtimeWSRelay`：前端 WS 接入 + 上游实时行情中继 |
| `src/services/symbol_list_service.py` | 各市场品种列表发现（内存 TTL 缓存 1h） |
| `src/scheduler.py` | 定时任务调度（已用于分析流程） |

### 2.4 已有鉴权（与目标差距）

- `src/auth.py` + `api/middlewares/auth.py`：**单管理员口令**鉴权
  （`ADMIN_AUTH_ENABLED` 开关 + PBKDF2 口令 + 签名 session cookie），保护 `/api/v1/*`。
- **差距**：这是「单管理员」模型，缺少多租户账号体系、订阅等级、按等级的数据/模型
  权限控制。需在其之上扩展，而非替换。

### 2.5 管理前端现状

- `server/api/app.py` 在 `static/index.html` 存在时托管 SPA；`server/src/webui_frontend.py`
  期望从 `server/apps/dsa-web` 构建产物拷贝到 `static/`。
- **现状**：仓库中 `server/apps/dsa-web` 与 `static/` 目前不存在。
- **决策变更**：不再新建独立 Web SPA。管理功能嵌入 Electron 客户端的 `Settings.vue`
  或新增 Admin 页面，作为授权用户的特权入口。

### 2.6 Bot 系统现状

- `server/bot/` 下已有完善的机器人框架：命令系统（分析/问答/市场/策略等）、多平台适配
  （钉钉、飞书、Discord）以及 `server/src/notification_sender/` 下十余种通知通道。
- **现状**：bot 与主进程绑定，通知发送依赖服务端运行，但账号隔离、按用户推送尚未实现。
- **定位变更**：Bot 系统是重要但非核心功能，列为独立后置阶段（详见 Bot 规划章节）。

---

## 三、目标架构

```
┌─────────────────────────────────┐        ┌──────────────────────────────────────────┐
│  Electron 客户端 (N台)           │        │       服务端 (mac mini / 云主机, 7×24)      │
│                                 │  HTTPS │  ┌──────────────────────────────────────┐  │
│  - 交易/图表/分析 UI             │◀──────▶│  │  FastAPI (server.py, 0.0.0.0:8100)   │  │
│  - 可配置服务端地址               │  WSS   │  │  - REST /api/v1/*  + /ws/market       │  │
│  - 管理员（授权用户）：           │        │  │  - 鉴权中间件 (admin + 多租户/订阅分级) │  │
│    · 服务状态 / 缓存管理          │        │  └──────────────────────────────────────┘  │
│    · 客户端监控 / 账号管理        │        │  ┌──────────────┐  ┌────────────────────┐  │
│    · 采集任务调度监控            │        │  │ 采集守护进程  │  │  Bot 推送服务 (未来) │  │
│  - 普通用户：基础行情/分析        │        │  │ Collector    │  │  - 多用户订阅管理   │  │
│                                 │        │  │  - WS实时写入 │  │  - 按用户配置推送   │  │
│  ⚠ 管理功能仅对「管理员」可见     │        │  │  - 定时补全   │  │  - 独立于客户端活跃 │  │
│    需要在客户端登录 admin 账号     │        │  │  - 标的预热   │  └────────────────────┘  │
│    并通过鉴权后方可使用           │        │  └──────┬───────┘                       │
│                                 │        │         ▼                                │
└─────────────────────────────────┘        │  ┌──────────────────────────────────────┐  │
                                           │  │  SQLite (WAL): 行情缓存 + 标的列表     │  │
                                           │  │  + 账号/订阅/用量 + 客户端会话         │  │
                                           │  └──────────────────────────────────────┘  │
                                           └──────────────────────────────────────────┘
```

### 关键设计原则

- **后端地址可配置**：客户端不再硬编码 `127.0.0.1:8100`，改为运行时从配置读取
  `serverBaseUrl`，支持「内置本地后端」与「连接远程服务端」两种模式平滑切换。
- **后端可独立运行**：服务端不依赖 Electron，通过进程守护（macOS `launchd`）或
  Docker 容器常驻；客户端只是其消费者之一。
- **采集与服务分离**：常驻「采集守护」负责持续写入缓存；REST/WS 负责对外服务，
  二者共享同一个 SQLite。
- **分层 + 需求驱动采集**：按数据粒度分层（L0 全市场快照 / L1 全市场日线归档 /
  L2 热门实时流+分钟线 / L3 长尾按需）。廉价高价值的全量储备，昂贵的只给热集合，
  **不全量实时抓取**（详见 Phase 3）。
- **渐进式鉴权**：管理功能复用现有 admin 口令鉴权；新增多租户 + 订阅分级保护数据 API，
  通过开关控制是否强制（内网阶段可关闭）。
- **管理平台内嵌于客户端**：不再维护独立的 Web SPA 前端工程，管理功能作为 Electron
  客户端的特权模式通过 admin 鉴权访问。

---

## 四、开发阶段规划

> 优先级：Phase 1 → 2 → 3 是内网跑通「常驻服务端 + 客户端连接」的最小闭环；
> Phase 4 是管理客户端功能嵌入；Phase 5 是商业化鉴权；Phase B 是 Bot 迁移（独立后置）。

### Phase 1：前后端解耦（客户端可连接远程后端）

目标：客户端能通过配置连接任意服务端地址，不再强绑定本地自动拉起的后端。

- [ ] **1.1 统一后端地址来源**
  - 新增 `client/src/renderer/src/service/serverConfig.ts`：导出 `getApiBase()` /
    `getWsUrl()`，从配置（IPC + localStorage 兜底）读取 `serverBaseUrl`，
    默认 `http://127.0.0.1:8100`。
  - 改造 8 处硬编码（见 §2.2）统一走 `serverConfig`。
- [ ] **1.2 主进程配置项**
  - `client/src/main/index.js`：在 `hivelogic-config.json` 增加 `server` 段
    （`mode: 'local' | 'remote'`、`remoteBaseUrl`、`token`）。
  - 新增 IPC：`get-server-config` / `set-server-config`，供渲染进程读取/保存。
- [ ] **1.3 本地后端按需启动**
  - `startFastApiServer()` 调整：仅当 `mode === 'local'` 时自动拉起；`remote` 模式
    跳过本地后端，直接连远程。
  - `before-quit` 仅在本地模式停止后端。
- [ ] **1.4 设置页 UI**
  - `Settings.vue` 新增「服务端连接」分组：模式切换（本地/远程）、远程地址输入、
    连接测试按钮（探测 `/api/health`）、访问令牌输入。
- [ ] **1.5 CORS / 跨域**
  - 远程模式下，前端 origin 与后端不同源；后端 `api/app.py` 的 `allowed_origins`
    需通过 `CORS_ORIGINS` 环境变量加入客户端来源（Electron `file://` 场景需评估，
    必要时保留 `CORS_ALLOW_ALL` 仅内网使用）。

产出验收：在 A 机器跑后端，B 机器客户端填入 `http://<A_IP>:8100` 可正常加载行情与图表。

---

### Phase 2：服务端独立部署（mac mini 常驻 + Docker 化）

目标：后端脱离 Electron，在 mac mini 上 7×24 常驻、开机自启、崩溃自拉起，
并为未来云迁移准备容器化方案。

- [ ] **2.1 部署文档与脚本**
  - 新增 `doc/deploy/server_setup_macos.md`：mac mini 环境准备
    （Python/uv 安装、克隆代码、`.env` 配置、数据目录规划）。
  - 新增 `deploy/run_server.sh`：以 `python main.py --serve-only --host 0.0.0.0
    --port 8100` 或 `uvicorn server:app` 启动（确认监听 `0.0.0.0`）。
- [ ] **2.2 进程守护（launchd）**
  - 新增 `deploy/com.hivelogic.server.plist`：`KeepAlive=true`、`RunAtLoad=true`、
    日志重定向到 `logs/`，崩溃自动重启。
  - 文档说明 `launchctl load/unload` 与日志查看方式。
- [ ] **2.3 数据目录与持久化**
  - 明确 `DATABASE_PATH` / 缓存 db / `.session_secret` / `.admin_password_hash`
    的服务端落盘路径（独立于代码目录，便于备份）。
  - 提供数据库备份脚本（SQLite WAL 安全备份）。
- [ ] **2.4 容器化（Docker）**
  - 新增 `Dockerfile`：基于 Python 3.12+ 镜像，安装 uv + 依赖，暴露 8100 端口，
    支持 `--serve-only` 模式启动。
  - 新增 `docker-compose.yml`：定义 `server` 服务 + 数据卷挂载（独立于容器生命周期
    的持久化目录）。
  - 文档说明 Docker 运行方式：`docker compose up -d` 即可启动守护。
  - **设计考量**：
    - 数据目录通过 volume 持久化，数据库/配置文件/日志不出容器。
    - 环境变量通过 `.env` 或 `docker-compose.override.yml` 传入。
    - 后续云迁移：镜像不变，只需替换编排层（launchd → Docker Compose → K8s）。
- [ ] **2.5 网络与安全（内网阶段）**
  - 固定内网 IP 或主机名；说明端口放行。
  - 内网阶段先用现有 admin 口令鉴权 + 简单访问令牌保护数据 API（Phase 5 再升级）。

产出验收：mac mini 重启后服务端自动恢复；`kill` 进程后被 launchd 拉起；
客户端断开/重连后行情不丢失；Docker 部署可替换 launchd 方案。

---

### Phase 3：持续行情采集与归档 + 标的列表预热（满足需求 1、2）

目标：服务端常驻采集，客户端「开箱即有数据」。

#### 设计基调：分层 + 需求驱动，而非全量实时

> 核心结论：**不实时抓取所有标的的实时行情**。按「数据粒度」分层——廉价高价值的
> （日线、全市场快照）全量储备；昂贵的（分钟线、实时流）只给真正有人看的热集合。
>
> 原因：A股 ~5400 + 港股 ~2800 + 美股 ~6000-8000 + 加密各 ~500，合计约 **2 万标的**。
> - 日线全量归档 ≈ 1 亿行（几个 GB），**便宜，值得全量做**；
> - 分钟线全量 ≈ **每年 12 亿行**，且绝大多数无人看，**不现实**；
> - A股/港股/美股数据源多为 REST，全量高频实时必然触发限流/封 IP（加密有聚合流，例外）。

四层采集模型：

| 层 | 范围 | 频率 | 落地策略 |
|----|------|------|----------|
| **L0 全市场快照** | 所有标的最新价/涨跌幅 | 盘中低频（数秒~数十秒） | 全市场快照接口一次拿回，供标的浏览器列表（满足需求1） |
| **L1 全市场日线归档** | 所有标的日线 | 每日收盘后增量 | 复用 `DownloadEngine`，**用全市场快照接口而非逐标的循环** |
| **L2 热门标的实时流+分钟线** | 被订阅的标的（自选∪在看∪运营重点） | 实时 | 引用计数订阅，LRU 退订；历史保留 |
| **L3 长尾冷门** | 其余标的 | 纯按需 | 客户端首次打开→现场拉一次→写缓存→升温进 L2 |

> AI 分析主要消费「日线 + 基本面 + 新闻」，由 L1 覆盖，**不依赖实时 tick**。

#### 任务清单

- [ ] **3.1 标的列表持久化与预热（L0 基础）**
  - 将 `SymbolListService` 结果落库（新表 `symbol_list`：market/symbol/name/updated_at）。
  - `GET /api/v1/market/symbols?market=...` 优先读库，秒级返回。
  - 客户端启动直接拉该接口渲染标的列表（满足需求 1）。
- [ ] **3.2 全市场行情快照采集（L0）**
  - 新增低频快照采集（A股用东财全量接口、加密用聚合流 `!ticker@arr`），维护「最新一份」
    全市场价格（最新价/涨跌幅），供标的浏览器；不长期归档。
- [ ] **3.3 全市场日线定时归档（L1）**
  - 见下「3.7 定时采集调度」；按市场收盘后增量补全所有标的日线。
- [ ] **3.4 实时行情写入缓存（L2）**
  - `RealtimeWSRelay` / WS 客户端中继实时 K 线时，未收盘 K 线以 `is_complete=0` 写入
    `kline_data`，收盘后更新为完整（落实 `local_database_plan` 待办项）。
  - 日终用 L1 官方收盘日线**校正**当天由实时流拼出的日线（以收盘值为准）。
- [ ] **3.5 订阅管理器（L2 关键缺口）**
  - 新增 `src/services/subscription_manager.py`：把【客户端需求 → 上游订阅】做
    **引用计数 + 多路复用 + LRU**——一个标的上游只订阅一次，扇出给 N 个客户端；
    无订阅者后按 LRU 退订上游（历史缓存保留）。
  - 改造 `RealtimeWSRelay` 走订阅管理器，**杜绝每客户端各开一条上游连接**。
  - 热集合来源：各客户端自选 ∪ 正在打开 ∪ 服务端运营配置，去重。
- [ ] **3.6 缓存优先读取强化 + 命中率埋点**
  - 复核 `DataFetcherManager.get_daily_data()` 的 cache-first 流程；增加命中率/缺口指标
    （供管理面板展示）。
- [ ] **3.7 定时采集调度（L1 核心）**
  - **按市场收盘后分别增量**（服务端按 CST/UTC+8）：

    | 任务 | 触发(CST) | 说明 |
    |------|-----------|------|
    | A股日线增量 | 15:30 | 15:00 收盘后，仅交易日 |
    | 港股日线增量 | 16:30 | 16:00 收盘后 |
    | 美股日线增量 | 06:00 | 美股 16:00 ET ≈ 次日 04:00–05:00 CST 收盘，留余量 |
    | 加密日线增量 | 08:10 | UTC 00:00=CST 08:00 为日线边界，收线后跑 |
    | 标的列表刷新 | 07:00 | 处理新增/退市/上下架 |
    | 夜间缺口对账补全 | 02:00 | 扫描 `cache_meta` 空洞，低优先级回填 |
    | 库维护(VACUUM/清理/备份) | 03:30 | 低峰期；分钟线按保留窗口清理 |

  - **增量而非全量**：只拉「上次缓存日期 → 今天」缺口（通常 1 根）。
  - **优先全市场快照接口**：A股收盘后一次拿回 ~5400 只 OHLC，避免 5400 次请求被限流。
  - **交易日判断**：复用 `get_open_markets_today()`，休市跳过对应市场任务。
  - **断电自愈（catch-up，7×24 必备）**：`schedule` 库不会补跑错过的任务。每个任务记录
    「上次成功日期」，服务启动时/每轮检查比对「应跑未跑」并补跑（幂等 upsert 保证安全）。
  - **幂等 + 重试**：依赖 `kline_data` 的 `UNIQUE(market,symbol,interval,timestamp)` 做 upsert；
    失败带退避重试，单标的失败不影响整体。
  - **可观测**：每任务的「上次成功时间/耗时/拉取条数/失败数」落表，供管理面板与 catch-up 依据。
  - **调度器实现**：**扩展现有 `Scheduler` 支持多定时点**。当前仅支持单一 `every().day.at()`，
    扩展为维护一个定时点列表，每个任务独立配置触发时间。**不引入 APScheduler**，理由如下：
    - 当前仅有 7 个固定时刻的任务，APScheduler 的 cron 表达式 + 线程池 + job store 持有化
      对于这个场景属于过度设计。
    - 引入 APScheduler 会增加：异步调度器配置（`AsyncIOScheduler`）、job store 选型
      （内存 vs SQLite 持久化）、序列化/反序列化、以及运行时线程池管理，这些复杂度
      在当前阶段没有收益。
    - catch-up 机制在业务层实现（记录「上次成功时间」逐任务校验），比 APScheduler 的
      misfire_grace_time 更可靠也更可控。
    - 未来如果任务数量膨胀到上百个、且需要动态增删/暂停/恢复、需要精确秒级 cron 表达式
      时，再考虑 APScheduler 不迟。
- [ ] **3.8 SQLite 并发防护：写队列 + busy-timeout**
  - SQLite 在 7×24 场景下，采集线程持续写入 + API 读取 + WS 实时中继写入，
    虽 WAL 模式允许读写并行，但写写冲突仍需防范。
  - **写队列**：所有写入操作（采集写入、缓存更新）通过单例队列串行化，
    避免多个协程/线程同时写 SQLite 导致 `database is locked`。
  - **busy-timeout**：SQLite 连接设置 `PRAGMA busy_timeout = 5000`，
    让写入冲突时等待最多 5 秒再报错，而非立即失败。
  - **连接管理**：API 只读路径使用单独的只读连接，与写连接分离，减少锁竞争。
  - 写入队列的实现应轻量：一个 `asyncio.Queue` + 单个 consumer 协程循环消费。
- [ ] **3.9 磁盘与清理策略**
  - 缓存大小统计接口 + 分钟级数据保留窗口/自动清理（落实 `local_database_plan` 待办项）。

产出验收：客户端冷启动立即看到标的列表与最新价；常用标的行情几乎全部命中本地缓存；
服务端在错过定时任务后（宕机/重启）能自动补跑当日日线，无数据缺口；
长时间运行无 `database is locked` 错误。

---

### Phase 4：管理功能嵌入客户端

目标：授权管理员可通过客户端查看和操作服务端，无需独立部署 Web SPA。

**设计思路变更**：原计划新建 `server/apps/dsa-web` 独立 SPA，现改为将管理功能
嵌入 Electron 客户端的特权模式。理由：
- 避免维护两套前端工程（Electron + Web SPA）
- 客户端已具备完整 UI 框架（Vue3 + Element Plus），复用现有组件即可
- 管理功能天然需要鉴权，客户端 admin 登录流程可与 Phase 5 统一

- [ ] **4.1 管理功能入口与鉴权**
  - `Settings.vue` 或新增 `AdminPanel.vue`：管理面板入口，仅对已登录 admin 账号可见。
  - 管理功能复用现有 `ADMIN_AUTH_ENABLED` 鉴权体系：用户通过 `POST /api/v1/auth/login`
    获取 admin session cookie，客户端存储并在管理 API 请求中携带。
  - 普通用户（未登录或非 admin）看不到管理入口。
  - 后端新增角色字段：admin 账号标记 `role: admin`，未来普通客户端账号为
    `role: user`（Phase 5 时启用）。
- [ ] **4.2 服务状态面板**
  - 后端新增 `GET /api/v1/admin/status`：进程运行时长、版本、各数据源健康、
    采集守护状态、WS 中继状态（`/api/ws/status` 已有）、调度任务状态。
  - 客户端渲染状态看板（卡片布局）：数据源健康指示灯、各调度任务最近执行时间、
    采集守护运行状态。
- [ ] **4.3 缓存管理**
  - 复用现有缓存 API（`/api/v1/cache/*`）+ 时间轴组件，提供按市场/标的的
    缓存覆盖热力图、手动触发下载/删除、下载任务进度展示。
- [ ] **4.4 客户端连接监控**
  - 后端维护活跃连接表（WS 连接 + 最近 REST 调用），新增
    `GET /api/v1/admin/clients`：列出连接的客户端（IP、账号、订阅等级、最近活跃、
    在订阅的标的）。
- [ ] **4.5 配置与调度管理**
  - 系统配置编辑（复用 `system_config` 服务）。
  - 调度任务手动触发和状态查看（基于「上次成功时间」落表）。
  - 管理员改密（复用 `auth` 现有能力）。
  - Phase 5 的账号/订阅管理入口在此预留。
- [ ] **4.6 清理旧管理前端代码**
  - 删除或冻结 `server/src/webui_frontend.py` 中指向 `static/` 的 SPA 托管逻辑。
  - 确认 `server/api/app.py` 的 `static/index.html` 检测逻辑可移除或保留为空。

产出验收：使用管理员账号登录客户端，可在设置中看到管理面板入口，进入后可查看
服务状态、缓存覆盖情况、在线客户端列表、手动触发采集任务。

---

### Phase 5：客户端鉴权与订阅分级（满足需求 5，商业化前置）

目标：多租户账号体系 + 订阅等级 + 按等级的数据/模型权限。

- [ ] **5.1 账号与订阅数据模型**
  - 新表：`accounts`（id/email/密码哈希/状态）、`subscriptions`（account_id/tier/
    到期时间）、`api_tokens`（account_id/token 哈希/设备/到期）、
    `usage_records`（用量计费/限流统计）。
  - 订阅等级定义：`tier`（如 free/pro/enterprise）→ 权限矩阵（可用市场、数据粒度、
    历史深度、可用模型、QPS/配额）。
- [ ] **5.2 客户端鉴权（区别于 admin 鉴权）**
  - 新增 `POST /api/v1/auth/client/login` 颁发 JWT/长期 token；客户端在请求头
    `Authorization: Bearer` 携带。
  - 扩展 `api/middlewares/auth.py`：对数据 API 增加「客户端 token 校验」分支，
    与现有 admin session 并存；通过开关 `CLIENT_AUTH_ENABLED` 控制（内网默认关闭）。
- [ ] **5.3 权限/配额执行（entitlement）**
  - 新增 `src/services/entitlement.py`：根据账号订阅等级判定某次请求是否被允许
    （市场/粒度/模型/配额），在数据 API 与 Agent/模型调用入口处拦截。
  - 超限返回 402/403 并附升级提示。
- [ ] **5.4 客户端登录 UI**
  - `Settings.vue`「服务端连接」分组接入账号登录/登出、显示当前订阅等级与配额。
- [ ] **5.5 管理面板账号管理**
  - Phase 4 的管理面板中增加账号 CRUD、订阅授予/到期、token 吊销、用量查看。

产出验收：不同等级账号登录后，可用市场/粒度/模型按矩阵生效；超额被正确拦截；
管理员可在客户端管理面板管理账号与订阅。

---

### Phase 6：稳定性、安全与上线准备

- [ ] **6.1 传输安全**：上线前为服务端启用 HTTPS/WSS（反向代理 Caddy/Nginx、
  应用层证书，或 Docker 部署时使用 Traefik/Caddy 自动 TLS）。
- [ ] **6.2 监控与告警**：结构化日志、健康检查、采集滞后/数据源失败告警。
- [ ] **6.3 限流与防滥用**：复用/扩展 `auth.py` 速率限制到数据 API；按账号配额。
- [ ] **6.4 备份与迁移**：数据库定期备份；从内网 mac mini 迁移到云主机的迁移文档
  （Docker 化后迁移流程精简为：镜像上传 → 云主机 pull → volume 挂载数据 → 启动）。
- [ ] **6.5 容器化生产部署**：规范多环境配置（dev/staging/prod 的 `docker-compose.override.yml`）、
  镜像版本管理、健康检查（`HEALTHCHECK` 指令）、日志采集（`docker logs` 或外部日志驱动）。
- [ ] **6.6 测试**：解耦回归（本地/远程模式）、采集守护稳定性、鉴权与权限矩阵单测/集成测试。

---

### Phase B：Bot / 消息推送系统服务端化（后置独立阶段）

目标：将 Bot 系统从当前与主进程/客户端绑定的模式，迁移为服务端常驻的多租户推送服务。

#### 现状

- `server/bot/` 已有一套完整的机器人命令框架和平台适配（钉钉、飞书、Discord）。
- `server/src/notification_sender/` 有 10+ 种通知通道实现（邮件、telegram、slack、pushplus 等）。
- **当前问题**：
  - 推送逻辑依赖服务端运行（已满足），但**用户偏好/订阅/凭证是全局的**，没有按用户隔离。
  - 用户希望接收特定标的的推送通知，且**不依赖客户端活跃** — 即使客户端关闭，
    服务端也应能根据用户预配置的推送通道主动发送消息。
  - 不同用户可能使用不同推送通道（有人用飞书、有人用 telegram），且订阅的标的和分析
    类型不同。

#### 任务清单

- [ ] **B.1 推送偏好数据模型**
  - 新表 `notification_preferences`：`account_id` / `channel`（枚举：telegram/email/feishu/discord/…）/
    `channel_config`（JSON：各通道所需的凭证/地址/Webhook URL）/ `subscribed_events`
    （JSON：订阅的事件类型列表，如 `signal_generated` / `price_breach` / `daily_report` 等）/
    `enabled` / `created_at` / `updated_at`。
  - 关联到 `accounts` 表（Phase 5 建立），每个用户可以配置多个推送通道、订阅不同事件。
- [ ] **B.2 推送事件总线**
  - 在服务端新增轻量事件总线（可用 `asyncio.Queue` 或基础 pub/sub 模式），
    当分析引擎/采集系统/策略引擎产生需要推送的事件时，发布到事件总线。
  - 事件类型：`price_alert` / `signal_generated` / `daily_report` / `system_alert` 等。
- [ ] **B.3 推送调度器**
  - 新增 `src/services/notification_dispatcher.py`：
    - 消费事件总线消息
    - 查询 `notification_preferences` 匹配当前事件的用户和通道
    - 按用户预配置的通道调用对应的 `notification_sender/*` 发送
    - 失败重试 + 退避
- [ ] **B.4 用户偏好配置 UI**
  - 客户端 `Settings.vue`「推送通知」分组：配置推送通道凭证、选择订阅的事件类型。
  - 通过 Phase 5 的鉴权绑定到具体账号，配置存储在服务端而非本地。
- [ ] **B.5 现有 Bot 命令整合**
  - `server/bot/commands/*` 中的功能（问市场、分析标的、策略推送等）在服务端常驻后
    可对接推送事件总线，例如「研究助手」的分析结果可通过事件总线触达订阅用户。

#### 设计与非设计

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 推送触发 | 事件驱动（事件总线），而非轮询 | bot 已具备异步通知能力；匹配推送场景 |
| 推送状态 | 服务端离线时推送丢失（不积攒）| Phase B 版本追求简洁，未来可加消息队列重试 |
| 与 bot 的关系 | bot 命令系统保持，推送作为 bot 能力的补充 | bot 命令用于实时互动，推送用于异步触达 |
| 优先级 | **Phase B 在所有 Phase 1–6 之后** | Bot 推送是增值功能，不影响核心闭环 |

---

## 五、里程碑与依赖关系

```
Phase 1 (解耦) ─→ Phase 2 (常驻部署+Docker) ─→ Phase 3 (持续采集) ─→ M1 内网闭环 ✅
                                                    │
                                                    └─→ Phase 4 (管理面板-嵌入客户端) ─→ M2 可运维
                                                                  │
                                                                  └─→ Phase 5 (鉴权/订阅) ─→ Ph6 (上线) ─→ M3 可商业化

Phase B (Bot 推送服务化) = 后置，不依赖 Phase 5，但可与 Phase 5 的 accounts 表配合
```

| 里程碑 | 包含阶段 | 价值 |
|--------|----------|------|
| M1 内网常驻闭环 | Phase 1–3 | 服务端 7×24 采集，客户端连接远程、开箱即有数据 |
| M2 可运维 | Phase 4 | 通过客户端管理面板监控服务、缓存、客户端连接 |
| M3 可商业化 | Phase 5–6 | 多租户鉴权、订阅分级、安全上线、生产部署 |
| M4 推送服务化 | Phase B（后置） | 多用户独立推送通道、事件驱动通知、不依赖客户端 |

---

## 六、关键技术决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 后端地址配置 | 客户端运行时配置 `serverBaseUrl`，本地/远程双模式 | 平滑过渡，开发期仍可本地内置后端 |
| 进程守护 | macOS `launchd`（后续云上用 Docker Compose） | mac mini 原生；Docker 化后迁移路径清晰 |
| 部署容器化 | Docker + docker-compose，数据卷持久化 | 与 launchd 共存（内网 launchd，云上容器），镜像不变 |
| 采集范围 | 分层 + 需求驱动（L0/L1 全量、L2/L3 按需） | 全量实时不经济也不合规；详见 Phase 3 |
| 日线增量方式 | 优先全市场快照接口，而非逐标的循环 | 避免 5000+ 次请求触发限流/封 IP |
| 定时调度 | 按市场收盘后分别增量 + catch-up 自愈 | 跨时区各市场收盘不同；7×24 须能补跑漏跑 |
| 调度器实现 | **扩展现有 `Scheduler` 支持多定时点，不引入 APScheduler** | 7 个固定时刻无需 APScheduler 的 cron/持久化/线程池；catch-up 在业务层更可靠 |
| SQLite 并发 | WAL + 写队列（`asyncio.Queue`）+ busy_timeout + 读写分离 | 7×24 写入场景下防 `database is locked`，轻量实现 |
| 实时订阅 | 引用计数 + 多路复用 + LRU 的订阅管理器 | 一标的上游只订一次，扇出多客户端，防限流 |
| 存储 | 沿用 SQLite（WAL），账号/订阅同库或独立 db | 复用现有基础设施，内网够用；分钟线热集合扩大或商业化放量时迁移 PostgreSQL/TimescaleDB |
| 客户端鉴权 | JWT/Bearer，独立于 admin session | 多端、可吊销、便于配额统计 |
| 鉴权开关 | `CLIENT_AUTH_ENABLED` 运行时开关 | 内网阶段免登录，商业化阶段强制 |
| 管理平台形态 | **内嵌于 Electron 客户端**，不独立维护 Web SPA | 避免双工程维护；复用现有 UI 框架和鉴权体系 |
| 管理平台鉴权 | 复用 admin 口令鉴权，区分 admin/user 角色 | Phase 4 即完成管理功能，无需等待 Phase 5 |
| Bot 推送 | 事件总线 + per-user 偏好配置 | 低优先级后置；事件驱动简化架构 |
| 云迁移路径 | Docker 镜像不变 → 云主机/容器平台 | launchd → Docker → K8s 逐级演进 |

---

## 七、主要文件变更清单（预估）

### 客户端（Electron / 渲染进程）
```
client/src/renderer/src/service/serverConfig.ts        # 新增：统一后端地址
client/src/renderer/src/service/marketDataService.ts   # 改：去硬编码
client/src/renderer/src/service/realtimeWSClient.ts    # 改：去硬编码
client/src/renderer/src/{Home,SymbolBrowser,MarketBrowser,Backtest,Portfolio}.vue  # 改
client/src/renderer/src/components/cache-timeline/CacheTimeline.vue                 # 改
client/src/renderer/src/AdminPanel.vue                 # 新增：管理面板（Phase 4）
client/src/renderer/src/Settings.vue                   # 改：服务端连接 + 管理入口 + 登录 + 推送偏好
client/src/main/index.js                               # 改：server 配置 + 按需启动后端
```

### 服务端（backend）
```
server/src/services/market_collector.py        # 新增：持续采集守护（L0/L1 定时 + catch-up）
server/src/services/subscription_manager.py    # 新增：实时订阅引用计数/多路复用/LRU
server/src/services/db_write_queue.py          # 新增：SQLite 写队列（Phase 3）
server/src/services/notification_dispatcher.py # 新增：推送事件总线/调度器（Phase B）
server/src/scheduler.py                         # 改：支持多定时点（数处小改动，不引入 APScheduler）
server/src/services/entitlement.py             # 新增：订阅权限/配额（Phase 5）
server/api/v1/endpoints/admin.py               # 新增：status/clients/采集任务监控 等（Phase 4）
server/api/v1/endpoints/auth.py                # 改：新增客户端登录（Phase 5）
server/api/middlewares/auth.py                 # 改：客户端 token 分支（Phase 5）
server/src/services/symbol_list_service.py     # 改：落库 + 预热
server/src/services/realtime_ws.py             # 改：实时写入缓存（Phase 3）
server/api/app.py                              # 改：lifespan 启动采集守护 + 写队列
server/src/repositories/ (accounts/subscriptions/...)  # 新增数据访问层（Phase 5）
```

### 部署与基础设施
```
deploy/run_server.sh
deploy/com.hivelogic.server.plist
Dockerfile                                       # 新增（Phase 2）
docker-compose.yml                               # 新增（Phase 2）
doc/deploy/server_setup_macos.md
doc/deploy/docker_deploy.md                      # 新增：容器化部署说明
```

### 废弃/冻结
```
server/src/webui_frontend.py                     # 冻结：不再用于 SPA 托管（Phase 4 清理）
server/apps/dsa-web/                             # 不再新建：管理功能已嵌入客户端
server/static/                                   # 不再需要托管 SPA
```

---

## 八、风险与注意事项

1. **CORS/同源**：Electron 渲染进程 origin 特殊，远程连接时需仔细配置后端
   `allowed_origins`，避免内网图省事开 `CORS_ALLOW_ALL` 带到生产。
2. **数据一致性**：实时未收盘 K 线写缓存需正确标记 `is_complete` 并在收盘后更新。
3. **SQLite 并发**：采集守护与 REST/WS 同库读写，需确保 WAL + 写队列 + busy_timeout；
   分钟线热集合扩大后写压力上升，须预留迁移 PostgreSQL/TimescaleDB 的迁移点。
4. **数据源限流**：日线增量务必走全市场快照接口而非逐标的循环；多个采集器（L0/L1/L2）
   共享数据源额度，需统一限速/优先级编排，避免互相挤兑触发封禁。
5. **存储增长**：日线全量约 1 亿行可控；分钟线全量不可行，须严格限定 L2 热集合 + 保留窗口。
6. **定时漏跑**：`schedule` 库不补跑错过任务，必须实现 catch-up，否则宕机当日出现数据缺口。
7. **实时连接放大**：严禁每客户端对上游各开一条连接，必须经订阅管理器多路复用，否则
   客户端增多即触发数据源限流。
8. **鉴权双轨**：admin 鉴权（Phase 4 管理面板）与客户端鉴权（Phase 5 数据 API）并存，
   中间件分支要清晰，避免越权。
9. **网络环境**：Binance/OKX 在大陆可能需代理，服务端需稳定代理配置。
10. **客户端离线降级**：远程服务端不可达时，客户端应给出明确提示与（可选）本地后端兜底。
11. **凭据安全**：内网测试机口令（如 mac mini）不得写入代码库；token/密码哈希落盘需
    权限 0600。
12. **管理面板安全**：管理功能嵌入客户端后，需确保管理 API 有服务端鉴权兜底，
    不能依赖客户端隐藏入口作为安全手段。
