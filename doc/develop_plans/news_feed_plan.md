# 新闻流页面（News Feed）功能计划

> 参考: TradingView 新闻流布局  
> 创建日期: 2026-04-25

---

## 1. 功能概述

实现一个独立的新闻流页面，作为应用的一个新模式/标签页类型。核心交互：

- **左侧面板**: 新闻标题组成的时间线列表，按时间倒序排列，支持无限滚动
- **右侧面板**: 新闻详情区域，展示选中新闻的完整信息
- **默认行为**: 进入页面时自动选中并展示最新一条新闻
- **实时感**: 支持手动刷新 + 可选的定时轮询获取最新新闻

### 1.1 用户故事

1. 用户点击侧边栏「新闻」按钮，进入新闻流页面
2. 左侧展示最新财经新闻的时间线，右侧自动显示第一条新闻详情
3. 用户可以按股票代码/关键词筛选新闻
4. 用户点击左侧任一新闻标题，右侧切换显示对应详情
5. 用户向下滚动左侧列表，自动加载更多历史新闻
6. 用户可以点击「查看原文」在浏览器中打开新闻来源

---

## 2. 架构设计

### 2.1 整体架构

```
┌────────────────────────────────────────────────────┐
│                  Electron 主窗口                     │
│  ┌──────────────────────────────────────────────┐  │
│  │            侧边栏 + 标签栏 (index.html)        │  │
│  ├──────────────────────────────────────────────┤  │
│  │        news.html (WebContentsView)            │  │
│  │  ┌──────────────┬───────────────────────┐    │  │
│  │  │   时间线列表    │     新闻详情           │    │  │
│  │  │   (左 30%)    │     (右 70%)           │    │  │
│  │  │              │                        │    │  │
│  │  │  [筛选栏]     │  标题                   │    │  │
│  │  │  ──────────  │  来源 · 时间             │    │  │
│  │  │  ● 标题1     │                        │    │  │
│  │  │    来源·时间  │  ┌──────────────────┐  │    │  │
│  │  │  ● 标题2     │  │   新闻正文/摘要     │  │    │  │
│  │  │    来源·时间  │  │                    │  │    │  │
│  │  │  ● 标题3     │  │                    │  │    │  │
│  │  │    来源·时间  │  └──────────────────┘  │    │  │
│  │  │  ...         │                        │    │  │
│  │  │              │  [查看原文]              │    │  │
│  │  └──────────────┴───────────────────────┘    │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 (Composition API + `<script setup>`) | 与项目一致 |
| UI 组件 | Element Plus (少量) + 自定义 CSS | 与项目一致 |
| 样式 | 手写 CSS (暗色主题, scoped) | 与项目一致 |
| HTTP | Fetch API + AbortSignal | 与项目一致 |
| 后端框架 | FastAPI | 与项目一致 |
| 数据存储 | SQLAlchemy (已有 `news_intel` 表) | 复用 |
| 新闻数据源 | Tavily / SerpAPI / Brave / Bocha / SearXNG | 已有多引擎支持 |

---

## 3. 后端 API 设计

### 3.1 新增端点

在 `backend/api/v1/endpoints/` 下新建 `news.py`，挂载到路由 `/api/v1/news`。

#### 3.1.1 `GET /api/v1/news` — 新闻列表

获取数据库中已存储的新闻列表（从 `news_intel` 表查询）。

**请求参数 (Query)**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 30 | 每页条数 (max 100) |
| `code` | str? | null | 股票代码筛选 |
| `keyword` | str? | null | 关键词搜索 (匹配标题/摘要) |
| `dimension` | str? | null | 维度筛选 (latest_news / risk_check / earnings 等) |
| `days` | int? | 7 | 时间范围 (天数) |

**响应**:
```json
{
  "total": 156,
  "page": 1,
  "page_size": 30,
  "items": [
    {
      "id": 1024,
      "title": "公司发布Q1业绩快报",
      "snippet": "公司公告显示...",
      "url": "https://example.com/news/123",
      "source": "新浪财经",
      "published_date": "2026-04-25T10:30:00",
      "code": "600519",
      "name": "贵州茅台",
      "dimension": "latest_news"
    }
  ]
}
```

#### 3.1.2 `GET /api/v1/news/{news_id}` — 新闻详情

**响应**:
```json
{
  "id": 1024,
  "title": "公司发布Q1业绩快报",
  "snippet": "公司公告显示，2026年第一季度营收同比增长20%...",
  "url": "https://example.com/news/123",
  "source": "新浪财经",
  "published_date": "2026-04-25T10:30:00",
  "fetched_at": "2026-04-25T11:00:00",
  "code": "600519",
  "name": "贵州茅台",
  "dimension": "latest_news",
  "query": "贵州茅台 600519 最新消息",
  "provider": "Tavily"
}
```

#### 3.1.3 `POST /api/v1/news/refresh` — 主动刷新新闻

手动触发为指定股票或通用关键词搜索最新新闻并入库。

**请求体**:
```json
{
  "codes": ["600519", "000858"],
  "keywords": ["A股 市场行情"],
  "max_results": 10
}
```

**响应**:
```json
{
  "fetched": 15,
  "new_count": 8,
  "message": "成功获取 15 条新闻，其中 8 条为新增"
}
```

#### 3.1.4 `GET /api/v1/news/timeline` — 时间线聚合

按日期分组返回新闻（供时间线展示优化）。

**请求参数 (Query)**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code` | str? | null | 股票代码筛选 |
| `days` | int? | 7 | 时间范围 |
| `limit` | int? | 100 | 总条数上限 |

**响应**:
```json
{
  "groups": [
    {
      "date": "2026-04-25",
      "items": [
        { "id": 1024, "title": "...", "source": "...", "published_date": "...", "code": "600519", "name": "贵州茅台" },
        { "id": 1023, "title": "...", "source": "...", "published_date": "...", "code": "000858", "name": "五粮液" }
      ]
    },
    {
      "date": "2026-04-24",
      "items": [...]
    }
  ]
}
```

### 3.2 Schema 定义

在 `backend/api/v1/schemas/` 下新建 `news.py`：

```python
class NewsListItem(BaseModel):
    id: int
    title: str
    snippet: str = ""
    url: str
    source: str = ""
    published_date: Optional[datetime] = None
    code: str = ""
    name: str = ""
    dimension: str = ""

class NewsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[NewsListItem]

class NewsDetailResponse(NewsListItem):
    fetched_at: Optional[datetime] = None
    query: str = ""
    provider: str = ""

class NewsRefreshRequest(BaseModel):
    codes: List[str] = []
    keywords: List[str] = []
    max_results: int = Field(default=10, ge=1, le=50)

class NewsRefreshResponse(BaseModel):
    fetched: int
    new_count: int
    message: str

class NewsTimelineGroup(BaseModel):
    date: str
    items: List[NewsListItem]

class NewsTimelineResponse(BaseModel):
    groups: List[NewsTimelineGroup]
```

### 3.3 Service 层

在 `backend/src/services/` 下新建 `news_service.py`，封装：

1. **查询逻辑**: 从 `news_intel` 表分页查询，支持筛选/搜索
2. **刷新逻辑**: 调用已有的 `SearchService.search_stock_news()` + `DatabaseManager.save_news_intel()`
3. **时间线聚合**: 按日期分组查询结果

---

## 4. 前端设计

### 4.1 文件结构

```
src/renderer/
├── news.html                          ← 新增: 页面入口 HTML
├── src/
│   ├── news.js                        ← 新增: Vue app 挂载入口
│   ├── News.vue                       ← 新增: 页面主组件
│   └── components/
│       └── news/
│           ├── NewsTimeline.vue        ← 新增: 左侧时间线列表
│           ├── NewsDetail.vue          ← 新增: 右侧新闻详情
│           └── NewsFilter.vue          ← 新增: 顶部筛选栏
```

### 4.2 组件设计

#### 4.2.1 `News.vue` — 主组件

```
职责:
- 管理页面整体布局 (左右分栏)
- 管理新闻列表数据、选中状态
- 协调子组件通信
- 提供 getBaseUrl() 和 fetch 调用

状态:
- newsList: ref([])          // 新闻列表
- selectedNews: ref(null)    // 当前选中的新闻
- loading: ref(false)        // 加载状态
- filter: reactive({})       // 筛选条件
- page: ref(1)               // 当前页码
- hasMore: ref(true)         // 是否有更多数据
```

#### 4.2.2 `NewsTimeline.vue` — 左侧时间线

```
职责:
- 按日期分组展示新闻标题
- 时间线样式 (竖线 + 圆点)
- 高亮当前选中项
- 滚动到底部时 emit 加载更多
- 显示来源和相对时间

Props:
- groups: Array           // 按日期分组的新闻
- selectedId: Number      // 选中的新闻 ID
- loading: Boolean        // 加载状态

Emits:
- select(newsItem)        // 选中某条新闻
- load-more()             // 触发加载更多
```

#### 4.2.3 `NewsDetail.vue` — 右侧详情

```
职责:
- 展示选中新闻的完整信息
- 标题、来源、时间、股票标签
- 摘要/正文内容
- 「查看原文」链接按钮
- 空状态提示

Props:
- news: Object            // 选中的新闻详情
- loading: Boolean        // 加载状态
```

#### 4.2.4 `NewsFilter.vue` — 顶部筛选

```
职责:
- 关键词搜索输入框
- 股票代码输入/选择
- 时间范围快捷选择 (今日/3天/7天/30天)
- 手动刷新按钮

Props:
- modelValue: Object      // 筛选条件 { keyword, code, days }

Emits:
- update:modelValue       // 筛选条件变更
- refresh()               // 手动刷新
```

### 4.3 页面样式规范

遵循项目现有暗色主题：

```css
/* 基础色板 */
--bg-primary: #1e1e1e;        /* 主背景 */
--bg-secondary: #252526;      /* 卡片/面板背景 */
--bg-hover: #2a2d2e;          /* 悬停态 */
--bg-active: #37373d;         /* 选中态 */
--border: #333;               /* 分割线 */
--text-primary: #e0e0e0;      /* 主文本 */
--text-secondary: #999;       /* 辅助文本 */
--accent: #4a9eff;            /* 强调色（蓝） */
--accent-green: #4caf50;      /* 正面 */
--accent-red: #f44336;        /* 负面 */

/* 时间线 */
--timeline-line: #333;        /* 时间线竖线 */
--timeline-dot: #4a9eff;      /* 时间点圆点 */
--timeline-dot-active: #fff;  /* 选中状态圆点 */
```

### 4.4 交互细节

| 交互 | 行为 |
|------|------|
| 首次加载 | 请求 `/api/v1/news/timeline` 获取最近 7 天新闻，自动选中第一条 |
| 点击左侧新闻 | 高亮该项，右侧展示详情（从列表数据获取，无需额外请求） |
| 滚动到底部 | 自动加载更多（增加 days 或 page） |
| 筛选条件变更 | 重置列表，重新请求 |
| 点击刷新按钮 | 调用 `/api/v1/news/refresh` 后重新加载列表 |
| 查看原文 | `window.open(url, '_blank')` 或通过 Electron shell 打开 |
| 键盘导航 | ↑/↓ 切换选中项 (可选，后续优化) |

---

## 5. 集成改动

### 5.1 构建配置

**`electron.vite.config.mjs`** — 添加 news 页面入口:

```javascript
// renderer.build.rollupOptions.input 中添加:
news: resolve('src/renderer/news.html')
```

### 5.2 Electron 主进程

**`src/main/index.js`** — 添加 news 模式支持:

1. 在模式常量中添加 `NEWS` 模式
2. 在 `switchMode()` / `createTabView()` 中处理 news 模式
3. 加载 `news.html` 页面

### 5.3 侧边栏入口

**`src/renderer/index.html`** — 添加新闻按钮:

```html
<button id="sidebar-news-btn" class="sidebar-btn" title="新闻">
  <!-- 新闻图标 SVG -->
</button>
```

**`src/renderer/src/index.js`** — 绑定点击事件，切换到 news 模式。

### 5.4 后端路由注册

**`backend/api/v1/router.py`** — 添加 news 路由:

```python
from backend.api.v1.endpoints.news import router as news_router
api_router.include_router(news_router, prefix="/news", tags=["news"])
```

---

## 6. 数据源策略

### 6.1 现有数据利用

项目已有完善的新闻搜索和存储机制：

- `news_intel` 表已存储大量历史新闻（每次股票分析时自动抓取）
- `SearchService` 支持 5 种搜索引擎故障转移
- 已有去重、缓存、负载均衡机制

### 6.2 新闻获取策略

1. **被动获取（已有）**: 用户进行股票分析时自动抓取相关新闻
2. **主动获取（新增）**: 用户在新闻页面点击「刷新」时调用 `POST /api/v1/news/refresh`
3. **定时获取（可选-后续）**: 后台定时任务为用户关注的股票定期抓取新闻

### 6.3 通用新闻

除了股票相关新闻，可考虑支持通用财经新闻搜索：

- 搜索关键词: "A股 市场行情"、"美股 财经新闻"、"加密货币 行情"
- 定期刷新通用关键词以保持新闻流活跃

---

## 7. 实施计划

### Phase 1: 后端 API（预计工作量：中）

| 步骤 | 任务 | 文件 |
|------|------|------|
| 1.1 | 创建 News Schema 定义 | `backend/api/v1/schemas/news.py` |
| 1.2 | 创建 News Service 层 | `backend/src/services/news_service.py` |
| 1.3 | 创建 News API 端点 | `backend/api/v1/endpoints/news.py` |
| 1.4 | 注册路由 | `backend/api/v1/router.py` |
| 1.5 | 测试 API 端点 | 手动测试 / Swagger UI |

### Phase 2: 前端页面（预计工作量：大）

| 步骤 | 任务 | 文件 |
|------|------|------|
| 2.1 | 创建 news.html 入口页 | `src/renderer/news.html` |
| 2.2 | 创建 news.js 挂载入口 | `src/renderer/src/news.js` |
| 2.3 | 创建 News.vue 主组件 | `src/renderer/src/News.vue` |
| 2.4 | 创建 NewsTimeline.vue | `src/renderer/src/components/news/NewsTimeline.vue` |
| 2.5 | 创建 NewsDetail.vue | `src/renderer/src/components/news/NewsDetail.vue` |
| 2.6 | 创建 NewsFilter.vue | `src/renderer/src/components/news/NewsFilter.vue` |
| 2.7 | 样式调试 (暗色主题适配) | 各 `.vue` 文件 |

### Phase 3: 集成（预计工作量：小）

| 步骤 | 任务 | 文件 |
|------|------|------|
| 3.1 | 构建配置添加 news 入口 | `electron.vite.config.mjs` |
| 3.2 | 主进程添加 news 模式 | `src/main/index.js` |
| 3.3 | 侧边栏添加新闻按钮 | `src/renderer/index.html` + `src/renderer/src/index.js` |
| 3.4 | 浏览器调试模式适配 | `src/renderer/src/browser-mock.js` (可选) |

### Phase 4: 优化（可选后续）

| 步骤 | 任务 | 说明 |
|------|------|------|
| 4.1 | 键盘导航 | ↑/↓ 键切换新闻 |
| 4.2 | 定时刷新 | 后台定时抓取关注股票新闻 |
| 4.3 | 新闻分类标签 | 按维度（公告/行情/研报/风险）分类展示 |
| 4.4 | 与图表联动 | 在图表页面侧边栏显示当前股票的新闻 |
| 4.5 | 新闻情感分析 | AI 标注新闻情感 (利好/利空/中性) |
| 4.6 | 推送通知 | 重要新闻推送到桌面通知 |

---

## 8. 建议实施顺序

```
Phase 1 (后端) → Phase 2 (前端) → Phase 3 (集成) → 测试验收 → Phase 4 (优化)
```

Phase 1 和 Phase 2 可以部分并行：在 Phase 1.1-1.2 完成后即可开始 Phase 2 的 UI 开发（使用 mock 数据）。

---

## 9. 注意事项

1. **API Key 用量**: 主动刷新功能会增加搜索 API 调用量，需要在 UI 上做适当的频率限制（如刷新按钮冷却时间）
2. **数据为空的处理**: 如果数据库中无新闻数据（首次使用），需友好引导用户进行首次刷新
3. **性能**: 左侧列表使用虚拟滚动或分页加载，避免一次加载过多 DOM 节点
4. **跨标签通信**: 如果用户在股票分析中产生了新的新闻数据，新闻页面应能感知（可通过轮询或 IPC 事件）
5. **Electron 兼容**: `window.open()` 在 Electron 中的行为需注意，建议使用 `shell.openExternal()` 通过 preload 暴露
