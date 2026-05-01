<template>
  <div class="symbol-browser">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <MarketTypeSelector
        :types="marketTypes"
        :active="activeMarketType"
        @change="handleMarketTypeChange"
      />
      <SymbolSearchBar
        v-model="searchQuery"
        :loading="searching"
        @search="handleSearch"
        @clear="handleClearSearch"
      />
    </div>

    <!-- 标的列表 -->
    <SymbolList
      :symbols="displaySymbols"
      :loading="loading"
      :active-market-type="activeMarketType"
      :search-query="searchQuery"
      @context-menu="handleContextMenu"
      @dblclick="handleDoubleClick"
      @reorder="handleReorder"
    />

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span class="status-count">共 {{ displaySymbols.length }} 个标的</span>
      <span v-if="lastUpdateTime" class="status-time">更新于 {{ lastUpdateTime }}</span>
    </div>

    <!-- 右键菜单 -->
    <SymbolContextMenu
      v-if="contextMenu.visible"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :symbol="contextMenu.symbol"
      :in-watchlist="isInWatchlist(contextMenu.symbol)"
      @open-chart="handleOpenChart"
      @market-analyze="handleMarketAnalyze"
      @toggle-watchlist="handleToggleWatchlist"
      @copy-code="handleCopyCode"
      @close="contextMenu.visible = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import MarketTypeSelector from './components/symbol-browser/MarketTypeSelector.vue'
import SymbolSearchBar from './components/symbol-browser/SymbolSearchBar.vue'
import SymbolList from './components/symbol-browser/SymbolList.vue'
import SymbolContextMenu from './components/symbol-browser/SymbolContextMenu.vue'

const API_BASE = 'http://127.0.0.1:8100/api/v1/market'

// 状态
const marketTypes = ref([])
const activeMarketType = ref('')
const symbols = ref([])
const searchResults = ref([])
const searchQuery = ref('')
const loading = ref(false)
const searching = ref(false)
const lastUpdateTime = ref('')
const watchlistSymbols = ref(new Set()) // 自选标的代码集合
const watchlistItems = ref([]) // 自选列表完整数据

// 实时行情轮询
let realtimeTimer = null
const REALTIME_INTERVAL = 8000 // 8秒

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  symbol: null
})

// 显示的列表：搜索模式用搜索结果，自选模式用自选列表，否则用完整列表
const displaySymbols = computed(() => {
  if (searchQuery.value && searchResults.value.length > 0) {
    return searchResults.value
  }
  if (searchQuery.value && searchResults.value.length === 0 && !searching.value) {
    return []
  }
  if (activeMarketType.value === 'watchlist') {
    return watchlistItems.value
  }
  return symbols.value
})

// 获取市场类型列表
async function fetchMarketTypes() {
  try {
    const res = await fetch(`${API_BASE}/types`)
    const data = await res.json()
    if (data.types) {
      // 在最前面插入"自选"虚拟类型
      const watchlistType = {
        type: 'watchlist',
        name: '自选',
        description: '自选标的列表',
        data_source: 'local',
        icon: '⭐',
        enabled: true
      }
      marketTypes.value = [watchlistType, ...data.types]
      // 默认选中"自选"
      activeMarketType.value = 'watchlist'
    }
  } catch (e) {
    console.error('[SymbolBrowser] 获取市场类型失败:', e)
  }
}

// 获取标的列表
async function fetchSymbols(marketType) {
  if (!marketType) return
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/symbols?type=${marketType}`)
    const data = await res.json()
    if (data.symbols) {
      symbols.value = data.symbols
      lastUpdateTime.value = new Date().toLocaleTimeString()
    }
  } catch (e) {
    console.error('[SymbolBrowser] 获取标的列表失败:', e)
  } finally {
    loading.value = false
  }
}

// 搜索标的
let searchTimer = null
async function handleSearch(query) {
  if (!query || query.trim().length === 0) {
    searchResults.value = []
    searching.value = false
    return
  }
  searching.value = true
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    try {
      const params = new URLSearchParams({ q: query })
      if (activeMarketType.value && activeMarketType.value !== 'watchlist') {
        params.set('type', activeMarketType.value)
      }
      const res = await fetch(`${API_BASE}/symbols/search?${params}`)
      const data = await res.json()
      if (data.symbols) {
        searchResults.value = data.symbols
      }
    } catch (e) {
      console.error('[SymbolBrowser] 搜索失败:', e)
    } finally {
      searching.value = false
    }
  }, 300)
}

function handleClearSearch() {
  searchQuery.value = ''
  searchResults.value = []
}

// ==================== 自选列表 ====================

async function fetchWatchlist() {
  try {
    const res = await fetch(`${API_BASE}/watchlist`)
    const data = await res.json()
    if (data.symbols) {
      watchlistItems.value = data.symbols
      watchlistSymbols.value = new Set(data.symbols.map((s) => s.symbol))
    }
  } catch (e) {
    console.error('[SymbolBrowser] 获取自选列表失败:', e)
  }
}

function isInWatchlist(symbol) {
  if (!symbol) return false
  return watchlistSymbols.value.has(symbol.symbol)
}

async function handleToggleWatchlist(symbol) {
  contextMenu.visible = false
  if (!symbol) return

  const inList = isInWatchlist(symbol)
  try {
    if (inList) {
      await fetch(`${API_BASE}/watchlist/${encodeURIComponent(symbol.symbol)}`, {
        method: 'DELETE'
      })
      watchlistSymbols.value.delete(symbol.symbol)
      watchlistItems.value = watchlistItems.value.filter((s) => s.symbol !== symbol.symbol)
    } else {
      await fetch(`${API_BASE}/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.symbol,
          name: symbol.name,
          market_type: symbol.market_type,
          exchange: symbol.exchange,
          data_source: symbol.data_source
        })
      })
      watchlistSymbols.value.add(symbol.symbol)
      watchlistItems.value.push({ ...symbol, sort_order: watchlistItems.value.length })
    }
  } catch (e) {
    console.error('[SymbolBrowser] 自选操作失败:', e)
  }
}

// ==================== 拖拽排序 ====================

async function handleReorder({ from, to }) {
  const list = [...watchlistItems.value]
  const [moved] = list.splice(from, 1)
  list.splice(to, 0, moved)
  watchlistItems.value = list

  // 后端同步排序
  try {
    const orderedSymbols = list.map((s) => s.symbol)
    await fetch(`${API_BASE}/watchlist/reorder`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols: orderedSymbols })
    })
  } catch (e) {
    console.error('[SymbolBrowser] 排序失败:', e)
    // 失败时重新获取
    fetchWatchlist()
  }
}

// ==================== 实时行情 ====================

async function fetchRealtimeQuotes() {
  const list = displaySymbols.value
  if (!list || list.length === 0) return

  // 按 market_type 分组获取 (最多50个)
  const groups = {}
  let count = 0
  for (const s of list) {
    if (count >= 50) break
    const mt = s.market_type || 'cn_stock'
    if (!groups[mt]) groups[mt] = []
    groups[mt].push(s.symbol)
    count++
  }

  for (const [mt, syms] of Object.entries(groups)) {
    try {
      const symbolsStr = syms.join(',')
      const res = await fetch(`${API_BASE}/realtime?symbols=${encodeURIComponent(symbolsStr)}&type=${mt}`)
      const data = await res.json()
      if (data.quotes) {
        // 构建 symbol -> quote 映射
        const quoteMap = {}
        for (const q of data.quotes) {
          quoteMap[q.symbol] = q
        }
        // 更新列表中的价格 (后端字段: price, change_percent)
        const updateList = (arr) => {
          return arr.map((item) => {
            const q = quoteMap[item.symbol]
            if (q) {
              return {
                ...item,
                current_price: q.price,
                change_percent: q.change_percent
              }
            }
            return item
          })
        }
        if (activeMarketType.value === 'watchlist') {
          watchlistItems.value = updateList(watchlistItems.value)
        } else if (!searchQuery.value) {
          symbols.value = updateList(symbols.value)
        }
        if (searchQuery.value) {
          searchResults.value = updateList(searchResults.value)
        }
      }
    } catch (e) {
      console.error('[SymbolBrowser] 获取实时行情失败:', e)
    }
  }
  lastUpdateTime.value = new Date().toLocaleTimeString()
}

function startRealtimePolling() {
  stopRealtimePolling()
  // 首次立即获取
  fetchRealtimeQuotes()
  realtimeTimer = setInterval(fetchRealtimeQuotes, REALTIME_INTERVAL)
}

function stopRealtimePolling() {
  if (realtimeTimer) {
    clearInterval(realtimeTimer)
    realtimeTimer = null
  }
}

// 切换市场类型
function handleMarketTypeChange(type) {
  activeMarketType.value = type
  searchQuery.value = ''
  searchResults.value = []
  if (type === 'watchlist') {
    fetchWatchlist().then(() => startRealtimePolling())
  } else {
    fetchSymbols(type).then(() => startRealtimePolling())
  }
}

// 右键菜单
function handleContextMenu({ event, symbol }) {
  event.preventDefault()
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.symbol = symbol
  contextMenu.visible = true
}

// 双击打开图表
function handleDoubleClick(symbol) {
  handleOpenChart(symbol)
}

// 在图表中打开
function handleOpenChart(symbol) {
  contextMenu.visible = false
  if (window.electronAPI?.openSymbolInChart) {
    window.electronAPI.openSymbolInChart({
      symbol: symbol.symbol,
      name: symbol.name,
      market_type: symbol.market_type,
      exchange: symbol.exchange,
      data_source: symbol.data_source
    })
  }
}

// 市场分析
function handleMarketAnalyze(symbol) {
  contextMenu.visible = false
  if (window.electronAPI?.openSymbolAnalysis) {
    window.electronAPI.openSymbolAnalysis({
      symbol: symbol.symbol,
      name: symbol.name,
      market_type: symbol.market_type
    })
  }
}

// 复制代码
function handleCopyCode(symbol) {
  contextMenu.visible = false
  navigator.clipboard.writeText(symbol.symbol).catch(() => {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = symbol.symbol
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  })
}

// 点击外部关闭右键菜单
function handleClickOutside() {
  contextMenu.visible = false
}

// 页面可见性: 不可见时停止轮询, 可见时恢复
function handleVisibility() {
  if (document.hidden) {
    stopRealtimePolling()
  } else {
    startRealtimePolling()
  }
}

// 监听搜索输入
watch(searchQuery, (val) => {
  handleSearch(val)
})

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('visibilitychange', handleVisibility)
  await fetchMarketTypes()
  // 默认加载自选列表
  await fetchWatchlist()
  // 启动实时行情轮询
  startRealtimePolling()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('visibilitychange', handleVisibility)
  stopRealtimePolling()
})
</script>

<style scoped>
.symbol-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  color: #cccccc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 13px;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #333;
  background: #252526;
  flex-shrink: 0;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 12px;
  border-top: 1px solid #333;
  background: #252526;
  font-size: 11px;
  color: #888;
  flex-shrink: 0;
}

.status-count {
  color: #999;
}

.status-time {
  color: #666;
}
</style>
