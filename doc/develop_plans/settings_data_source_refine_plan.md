# 设置 - 数据源页面重构方案

> 目标：将数据源设置页面从"平铺字段列表"重构为类似 AI 模型设置的"渠道列表 + 拖拽排序"交互模式。

---

## 1. 数据源清单

| 数据源 | 类型 | 认证方式 | 默认开启 | 说明 |
|--------|------|----------|----------|------|
| **AKShare** | Python 包 | 无需 Key | ✅ | 聚合多个数据源（新浪/东财/腾讯），免费。内含 `akshare_sina`、`akshare_em`、`akshare_qq`(腾讯) 三个子源 |
| **Efinance** | Python 包 | 无需 Key | ✅ | 东方财富爬虫封装，免费，有防封策略 |
| **通达信 (Pytdx)** | 自建服务器 | 服务器地址+端口 | ❌ | 需自行部署通达信数据服务器 |
| **Tushare** | 付费 API | API Token | ❌ | Tushare Pro 金融数据接口 |
| **TickFlow** | 付费 API | API Key | ❌ | 支持 A 股/港股/美股/ETF，REST+WebSocket |
| **Longbridge** | 付费 API | App Key + Secret + Access Token | ❌ | 长桥证券数据接口 |

### 数据源能力矩阵

| 数据源 | K 线 | 实时行情 | 标的列表 | 财务数据 | 筹码分布 |
|--------|------|----------|----------|----------|----------|
| AKShare | ✅ | ✅(sina/em/腾讯) | ✅ | ✅ | ✅ |
| Efinance | ✅ | ✅ | ✅ | - | - |
| 通达信 | ✅ | ✅ | ✅ | - | - |
| Tushare | ✅ | ✅ | ✅ | ✅ | - |
| TickFlow | ✅ | ✅(WS) | ✅ | ✅ | - |
| Longbridge | ✅ | ✅ | ✅ | - | - |

---

## 2. 新闻搜索源清单

| 搜索源 | 认证方式 | 说明 |
|--------|----------|------|
| **Anspire** | API Key | 新闻检索 |
| **Tavily** | API Key | AI 搜索引擎 |
| **SerpAPI** | API Key | Google 搜索代理 |
| **Brave** | API Key | Brave Search |
| **Bocha** | API Key | 博查搜索（最高优先级） |
| **Minimax** | API Key | MiniMax 搜索（最低优先级） |
| **SearXNG（自建）** | Base URL | 自建 SearXNG 实例，无配额 |
| **SearXNG（公共）** | 无需配置 | 自动从 searx.space 发现公共实例并轮询 |

---

## 3. 设置开关项

### 数据源开关
| 开关 | 配置 Key | 说明 |
|------|----------|------|
| 盘中实时技术面 | `ENABLE_REALTIME_TECHNICAL_INDICATORS` | 盘中用实时价计算 MA 指标 |
| 实时行情 | `ENABLE_REALTIME_QUOTE` | 启用实时行情推送 |
| 筹码分布 | `ENABLE_CHIP_DISTRIBUTION` | 启用筹码分布分析 |

### 新闻源参数
| 参数 | 配置 Key | 说明 |
|------|----------|------|
| 最大时效 | `NEWS_MAX_AGE_DAYS` | 新闻最大时效上限（天） |
| 策略窗口档位 | `NEWS_STRATEGY_PROFILE` | ultra_short/short/medium/long |
| 偏离阈值 | `BIAS_THRESHOLD` | MA5 偏离阈值（%） |

---

## 4. UI 重构方案

### 4.1 设计思路

参照现有 AI 模型渠道编辑器（`activeCategory === 'ai_model'`），将 `data_source` 分类页面改造为两个独立的渠道编辑器：

```
┌─────────────────────────────────────────────────┐
│ 📊 数据源                                        │
├─────────────────────────────────────────────────┤
│                                                 │
│ ┌─ 行情数据源渠道 ─────────────────────────────┐ │
│ │ 快速添加渠道 [提供商 ▾] [+ 添加渠道]        │ │
│ │ 2/4 已启用                                   │ │
│ │                                              │ │
│ │ ⠿ ✅ akshare    │ AKShare   │ 免费  │ ▶  │ │
│ │ ⠿ ✅ efinance   │ Efinance  │ 免费  │ ▶  │ │
│ │ ⠿ ☐ tushare    │ Tushare   │ ⚠Key │ ▶  │ │
│ │ ⠿ ☐ tickflow   │ TickFlow  │ ⚠Key │ ▶  │ │
│ │                                              │ │
│ │ ── 开关 ─────────────────────────────────── │ │
│ │ [✅] 盘中实时技术面                          │ │
│ │ [✅] 实时行情                                │ │
│ │ [☐] 筹码分布                                │ │
│ └──────────────────────────────────────────────┘ │
│                                                 │
│ ┌─ 新闻搜索源渠道 ─────────────────────────────┐ │
│ │ 快速添加渠道 [提供商 ▾] [+ 添加渠道]        │ │
│ │ 2/4 已启用                                   │ │
│ │                                              │ │
│ │ ⠿ ✅ bocha     │ Bocha     │ ✓Key  │ ▶  │ │
│ │ ⠿ ✅ tavily    │ Tavily    │ ✓Key  │ ▶  │ │
│ │ ⠿ ☐ searxng   │ SearXNG自建│ ⚠URL │ ▶  │ │
│ │ ⠿ ☐ searxng_pub│ SearXNG公共│ 自动  │ ▶  │ │
│ │                                              │ │
│ │ ── 参数 ─────────────────────────────────── │ │
│ │ 最大时效    [7] 天                           │ │
│ │ 策略窗口档位 [short ▾]                       │ │
│ │ 偏离阈值    [3.0] %                         │ │
│ └──────────────────────────────────────────────┘ │
│                                                 │
│ ┌─ 其他参数 ────────────────────────────────────┐ │
│ │ （基本面管线、熔断冷却等高级参数）           │ │
│ └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 4.2 渠道卡片交互

每个渠道卡片包含：
- **拖拽手柄** `⠿`：上下拖拽调整优先级顺序
- **启用开关**：checkbox 控制是否启用
- **名称/标签**：提供商显示名
- **状态徽章**：
  - `免费`：无需认证的数据源（绿色）
  - `✓Key`：已填写密钥（绿色）
  - `⚠Key`/`⚠URL`：未填写必需凭证（橙色警告）
  - `自动`：无需配置（蓝色）
- **展开箭头** `▶`：点击展开编辑区域

展开后可编辑：
- 数据源：API Key / Token / 服务器地址等（视提供商而定）
- 新闻源：API Key / Base URL

### 4.3 预设定义

```javascript
// 行情数据源预设
const dataSourcePresets = {
  akshare:    { label: 'AKShare（新浪/东财/腾讯）', authType: 'none', defaultEnabled: true, priority: 0, subSources: ['akshare_sina', 'akshare_em', 'tencent'] },
  efinance:   { label: 'Efinance（东方财富）', authType: 'none', defaultEnabled: true, priority: 1 },
  pytdx:      { label: '通达信 (Pytdx)', authType: 'server', fields: ['host', 'port', 'servers'], defaultEnabled: false },
  tushare:    { label: 'Tushare Pro', authType: 'token', fields: ['token'], defaultEnabled: false },
  tickflow:   { label: 'TickFlow', authType: 'apiKey', fields: ['apiKey'], defaultEnabled: false },
  longbridge: { label: 'Longbridge（长桥）', authType: 'multi', fields: ['appKey', 'appSecret', 'accessToken'], defaultEnabled: false },
}

// 新闻搜索源预设
const newsSourcePresets = {
  bocha:       { label: 'Bocha', authType: 'apiKey', fields: ['apiKeys'] },
  anspire:     { label: 'Anspire', authType: 'apiKey', fields: ['apiKeys'] },
  tavily:      { label: 'Tavily', authType: 'apiKey', fields: ['apiKeys'] },
  serpapi:     { label: 'SerpAPI', authType: 'apiKey', fields: ['apiKeys'] },
  brave:       { label: 'Brave Search', authType: 'apiKey', fields: ['apiKeys'] },
  minimax:     { label: 'MiniMax', authType: 'apiKey', fields: ['apiKeys'] },
  searxng:     { label: 'SearXNG（自建）', authType: 'url', fields: ['baseUrls'] },
  searxng_pub: { label: 'SearXNG（公共实例）', authType: 'none' },
}
```

### 4.4 数据持久化

**后端配置 Key 映射：**

| 渠道列表 | 后端 Key | 格式 |
|----------|----------|------|
| 行情数据源排序 | `REALTIME_SOURCE_PRIORITY` | 逗号分隔，akshare 展开为子源 `tencent,akshare_sina,akshare_em` |
| 行情渠道启用 | 新增 `DATA_SOURCE_CHANNELS` | JSON 数组（含顺序、启用状态、凭证映射） |
| 新闻源排序 | 新增 `NEWS_SOURCE_PRIORITY` | 逗号分隔 `bocha,tavily,brave,serpapi,searxng,minimax` |
| 新闻渠道启用 | 新增 `NEWS_SOURCE_CHANNELS` | JSON 数组 |

> **兼容方案**：如果不想新增 Key，可以从现有 `REALTIME_SOURCE_PRIORITY` 和各 `*_API_KEYS` 字段反推渠道列表状态。推荐渐进方案：前端保存完整渠道结构，同时同步更新原有字段以兼容后端逻辑。

### 4.5 默认渠道行为

- **数据源**：`akshare`、`efinance` 两个免费源默认存在于渠道列表中并启用，按此顺序排列（akshare 内含 tencent/sina/em 三个子源）
- **新闻源**：首次加载时渠道列表为空；用户添加后保存
- **拖拽排序**：列表顺序即为调用优先级（从上到下）

---

## 5. 实现计划

### Phase 1: 前端 UI 框架（数据源渠道编辑器）

**文件**：`src/renderer/src/Settings.vue`

| 步骤 | 内容 |
|------|------|
| 1.1 | 在 `activeCategory === 'data_source'` 时渲染专用编辑器（类似 `ai_model` 的 `llm-editor`） |
| 1.2 | 定义 `dataSourcePresets` 和 `newsSourcePresets` 预设对象 |
| 1.3 | 实现 `dataSourceChannels` 和 `newsSourceChannels` 响应式数组 |
| 1.4 | 实现"快速添加渠道"下拉选择 + 添加按钮 |
| 1.5 | 实现渠道卡片列表（启用开关、名称、状态徽章、展开/折叠） |
| 1.6 | 展开区域：根据 `authType` 渲染对应字段（apiKey/token/host+port/url） |
| 1.7 | 拖拽排序（使用 HTML5 Drag & Drop 或轻量库 `sortablejs`） |
| 1.8 | 数据源开关区域（三个 switch） |
| 1.9 | 新闻源参数区域（三个输入框） |

### Phase 2: 数据加载与保存逻辑

| 步骤 | 内容 |
|------|------|
| 2.1 | 页面加载时，从 DSA 后端读取 `REALTIME_SOURCE_PRIORITY` + 各凭证 Key → 反推渠道列表 |
| 2.2 | 默认源（akshare/efinance）如果不在列表中则自动补充 |
| 2.3 | 新闻源从各 `*_API_KEYS` / `SEARXNG_BASE_URLS` / `SEARXNG_PUBLIC_INSTANCES_ENABLED` 反推 |
| 2.4 | 保存时：渠道列表顺序 → 更新 `REALTIME_SOURCE_PRIORITY` |
| 2.5 | 保存时：各渠道凭证 → 更新对应后端 Key（如 `TUSHARE_TOKEN`、`TICKFLOW_API_KEY`） |
| 2.6 | 新闻源保存同理：排序 → `NEWS_SOURCE_PRIORITY`（新增），凭证 → 对应 `*_API_KEYS` |

### Phase 3: 后端适配

| 步骤 | 内容 |
|------|------|
| 3.1 | `config_registry.py` 新增 `NEWS_SOURCE_PRIORITY` 配置项 |
| 3.2 | `config.py` 新增 `news_source_priority` 字段 |
| 3.3 | 搜索服务（`search_service.py`）读取 `NEWS_SOURCE_PRIORITY` 决定搜索源调用顺序 |
| 3.4 | 确保所有数据源凭证 Key 已在 registry 注册且 category = `data_source` |

### Phase 4: 拖拽排序优化

| 步骤 | 内容 |
|------|------|
| 4.1 | 引入 `sortablejs`（或纯 HTML5 DnD），为渠道卡片添加拖拽手柄 |
| 4.2 | 拖拽结束后自动标记 dirty 状态 |
| 4.3 | 视觉反馈：拖拽时半透明 + 插入指示线 |

### Phase 5: 隐藏已管理字段

| 步骤 | 内容 |
|------|------|
| 5.1 | 定义 `DATA_SOURCE_MANAGED_KEYS` 集合（类似 AI 模型的 `AI_MODEL_HIDDEN_KEYS`） |
| 5.2 | 在 `filteredActiveItems` 中过滤掉已在渠道编辑器管理的字段 |
| 5.3 | 保留"基本面管线"、"熔断"等高级参数在分组列表中展示 |

---

## 6. 技术要点

1. **不引入额外路由**：整个编辑器仍在 Settings.vue 的 `data_source` 分类下渲染
2. **兼容现有后端**：不改变现有 Key 语义，仅在前端做渠道抽象 → Key 映射
3. **渐进式**：Phase 1-2 即可上线，Phase 3-4 可后续迭代
4. **拖拽库选择**：推荐 `sortablejs`（~30KB gzip），已广泛使用且无框架依赖
5. **CSS 复用**：复用现有 `.channel-card`、`.channel-row`、`.channel-body` 样式类

---

## 7. 配置 Key 对照表

### 行情数据源
| 渠道 ID | 对应后端 Key | 类型 |
|---------|-------------|------|
| `akshare` | `REALTIME_SOURCE_PRIORITY` 中展开为 `tencent,akshare_sina,akshare_em` | 无凭证 |
| `efinance` | （内置） | 无凭证 |
| `pytdx` | `PYTDX_HOST` + `PYTDX_PORT` + `PYTDX_SERVERS` | 服务器 |
| `tushare` | `TUSHARE_TOKEN` | Token |
| `tickflow` | `TICKFLOW_API_KEY` | API Key |
| `longbridge` | `LONGBRIDGE_APP_KEY` + `LONGBRIDGE_APP_SECRET` + `LONGBRIDGE_ACCESS_TOKEN` | 多字段 |

### 新闻搜索源
| 渠道 ID | 对应后端 Key | 类型 |
|---------|-------------|------|
| `bocha` | `BOCHA_API_KEYS` | API Keys |
| `anspire` | `ANSPIRE_API_KEYS` | API Keys |
| `tavily` | `TAVILY_API_KEYS` | API Keys |
| `serpapi` | `SERPAPI_API_KEYS` | API Keys |
| `brave` | `BRAVE_API_KEYS` | API Keys |
| `minimax` | `MINIMAX_API_KEYS` | API Keys |
| `searxng` | `SEARXNG_BASE_URLS` | URLs |
| `searxng_pub` | `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Boolean |