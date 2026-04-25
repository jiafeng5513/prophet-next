<template>
  <div class="news-page">
    <!-- 顶部筛选栏 -->
    <NewsFilter
      v-model="filter"
      :loading="refreshing"
      @refresh="handleRefresh"
    />

    <div class="news-body">
      <!-- 左侧时间线 -->
      <div class="news-timeline-panel">
        <NewsTimeline
          :groups="timelineGroups"
          :selected-id="selectedNewsId"
          :loading="loading"
          @select="handleSelect"
          @load-more="handleLoadMore"
        />
      </div>

      <!-- 右侧详情 -->
      <div class="news-detail-panel">
        <NewsDetail :news="selectedNews" :loading="detailLoading" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import NewsFilter from './components/news/NewsFilter.vue'
import NewsTimeline from './components/news/NewsTimeline.vue'
import NewsDetail from './components/news/NewsDetail.vue'

// DSA 端口
let dsaPort = 8100

function getBaseUrl() {
  return `http://127.0.0.1:${dsaPort}`
}

// 状态
const loading = ref(false)
const detailLoading = ref(false)
const refreshing = ref(false)

const filter = reactive({
  keyword: '',
  code: '',
  days: 7
})

const timelineGroups = ref([])
const selectedNewsId = ref(null)
const selectedNews = ref(null)

// 所有新闻的平铺映射 (id -> item)
const newsMap = computed(() => {
  const map = {}
  for (const group of timelineGroups.value) {
    for (const item of group.items) {
      map[item.id] = item
    }
  }
  return map
})

// 加载时间线数据
async function fetchTimeline() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('days', filter.days)
    params.set('limit', '200')
    if (filter.code) params.set('code', filter.code)
    if (filter.keyword) params.set('keyword', filter.keyword)

    const resp = await fetch(
      `${getBaseUrl()}/api/v1/news/timeline?${params.toString()}`,
      { signal: AbortSignal.timeout(10000) }
    )
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const data = await resp.json()
    timelineGroups.value = data.groups || []

    // 默认选中第一条
    if (timelineGroups.value.length > 0 && timelineGroups.value[0].items.length > 0) {
      const first = timelineGroups.value[0].items[0]
      await handleSelect(first)
    } else {
      selectedNewsId.value = null
      selectedNews.value = null
    }
  } catch (e) {
    console.error('获取新闻时间线失败:', e)
    timelineGroups.value = []
  } finally {
    loading.value = false
  }
}

// 获取新闻详情
async function fetchDetail(newsId) {
  detailLoading.value = true
  try {
    const resp = await fetch(
      `${getBaseUrl()}/api/v1/news/${newsId}`,
      { signal: AbortSignal.timeout(5000) }
    )
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    selectedNews.value = await resp.json()
  } catch (e) {
    console.error('获取新闻详情失败:', e)
    // 降级：使用时间线中的摘要信息
    selectedNews.value = newsMap.value[newsId] || null
  } finally {
    detailLoading.value = false
  }
}

// 选中新闻
async function handleSelect(item) {
  selectedNewsId.value = item.id
  await fetchDetail(item.id)
}

// 加载更多（增大时间范围）
function handleLoadMore() {
  if (filter.days < 90) {
    filter.days = Math.min(filter.days + 7, 90)
  }
}

// 手动刷新
async function handleRefresh() {
  refreshing.value = true
  try {
    const body = {}
    if (filter.code) {
      body.codes = [filter.code]
    }
    if (filter.keyword) {
      body.keywords = [filter.keyword]
    }
    // 如果没有指定筛选条件，搜索通用财经新闻
    if (!body.codes && !body.keywords) {
      body.keywords = ['A股 市场行情 最新消息']
    }
    body.max_results = 10

    await fetch(`${getBaseUrl()}/api/v1/news/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30000)
    })
  } catch (e) {
    console.error('刷新新闻失败:', e)
  } finally {
    refreshing.value = false
    // 刷新后重新加载时间线
    await fetchTimeline()
  }
}

// 筛选条件变化时重新加载
watch(
  () => ({ keyword: filter.keyword, code: filter.code, days: filter.days }),
  () => {
    fetchTimeline()
  },
  { deep: true }
)

// 初始化
onMounted(async () => {
  // 从主进程获取 DSA 端口
  if (window.electronAPI && window.electronAPI.getDsaConfig) {
    const config = await window.electronAPI.getDsaConfig()
    dsaPort = config.port || 8100
  }

  // 监听 DSA 状态变化
  if (window.electronAPI && window.electronAPI.onDsaStatusChanged) {
    window.electronAPI.onDsaStatusChanged(async (data) => {
      dsaPort = data.port || dsaPort
    })
  }

  await fetchTimeline()
})
</script>

<style scoped>
.news-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1e1e1e;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.news-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.news-timeline-panel {
  width: 340px;
  min-width: 280px;
  border-right: 1px solid #333;
  overflow-y: auto;
  flex-shrink: 0;
}

.news-detail-panel {
  flex: 1;
  overflow-y: auto;
}

/* 滚动条样式 */
.news-timeline-panel::-webkit-scrollbar,
.news-detail-panel::-webkit-scrollbar {
  width: 6px;
}

.news-timeline-panel::-webkit-scrollbar-track,
.news-detail-panel::-webkit-scrollbar-track {
  background: transparent;
}

.news-timeline-panel::-webkit-scrollbar-thumb,
.news-detail-panel::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.news-timeline-panel::-webkit-scrollbar-thumb:hover,
.news-detail-panel::-webkit-scrollbar-thumb:hover {
  background: #777;
}
</style>
