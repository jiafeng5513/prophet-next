<template>
  <div class="symbol-list" ref="containerRef" @scroll="onScroll">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="symbols.length === 0" class="empty-state">
      <span class="empty-icon">📭</span>
      <span>暂无标的数据</span>
    </div>

    <!-- 虚拟滚动列表 -->
    <template v-else>
      <div class="list-header">
        <span v-if="isWatchlist" class="col-drag"></span>
        <span class="col-symbol" :style="{ width: colWidths.symbol + 'px' }">代码
          <span class="col-resizer" @mousedown.prevent="startResize($event, 'symbol')"></span>
        </span>
        <span class="col-name" :style="{ width: colWidths.name + 'px' }">名称
          <span class="col-resizer" @mousedown.prevent="startResize($event, 'name')"></span>
        </span>
        <span class="col-price" :style="{ width: colWidths.price + 'px' }">最新价
          <span class="col-resizer" @mousedown.prevent="startResize($event, 'price')"></span>
        </span>
        <span class="col-change" :style="{ width: colWidths.change + 'px' }">涨跌幅</span>
      </div>
      <div class="virtual-list" :style="{ height: totalHeight + 'px' }">
        <div
          class="virtual-list-viewport"
          :style="{ transform: `translateY(${offsetY}px)` }"
        >
          <div
            v-for="item in visibleItems"
            :key="item.symbol"
            :class="[
              'symbol-row',
              { 'symbol-row-alt': item._index % 2 === 1 },
              { 'drag-over': dragOverIndex === item._index }
            ]"
            :draggable="isWatchlist"
            @contextmenu="$emit('context-menu', { event: $event, symbol: item })"
            @dblclick="$emit('dblclick', item)"
            @dragstart="onDragStart($event, item._index)"
            @dragover.prevent="onDragOver($event, item._index)"
            @dragleave="onDragLeave"
            @drop="onDrop($event, item._index)"
            @dragend="onDragEnd"
          >
            <span v-if="isWatchlist" class="col-drag" title="拖拽排序">⠿</span>
            <span class="col-symbol" :style="{ width: colWidths.symbol + 'px' }">
              <span class="symbol-code" v-html="highlight(item.symbol)"></span>
            </span>
            <span class="col-name" :style="{ width: colWidths.name + 'px' }" :title="item.name" v-html="highlight(item.name)"></span>
            <span class="col-price" :style="{ width: colWidths.price + 'px' }" :class="priceClass(item)">
              {{ formatPrice(item.current_price) }}
            </span>
            <span class="col-change" :style="{ width: colWidths.change + 'px' }" :class="changeClass(item)">
              {{ formatChange(item.change_percent) }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  symbols: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  activeMarketType: { type: String, default: '' },
  searchQuery: { type: String, default: '' }
})

const emit = defineEmits(['context-menu', 'dblclick', 'reorder'])

const isWatchlist = computed(() => props.activeMarketType === 'watchlist')

const ROW_HEIGHT = 32
const BUFFER_COUNT = 10

// ==================== 列宽调整 ====================

// 各列最小宽度（保证表头文字+padding不换行）
const COL_MIN_WIDTHS = { symbol: 50, name: 56, price: 56, change: 56 }
// 各列宽度比例（symbol:name:price:change）
const COL_RATIOS = { symbol: 0.18, name: 0.40, price: 0.21, change: 0.21 }

const colWidths = ref({
  symbol: 60,
  name: 160,
  price: 64,
  change: 64
})

function initColWidths() {
  if (!containerRef.value) return
  const containerWidth = containerRef.value.clientWidth
  // 减去左右padding(12*2)、分栏线(3条*1px)、列间padding(4列*16px)
  const overhead = 24 + 3 + 64
  const available = containerWidth - overhead
  if (available <= 0) return

  const keys = ['symbol', 'name', 'price', 'change']
  keys.forEach(key => {
    const w = Math.floor(available * COL_RATIOS[key])
    colWidths.value[key] = Math.max(COL_MIN_WIDTHS[key], w)
  })
}

let resizingCol = null
let resizeStartX = 0
let resizeStartWidth = 0
let hasManuallyResized = false

function startResize(e, col) {
  resizingCol = col
  resizeStartX = e.clientX
  resizeStartWidth = colWidths.value[col]
  hasManuallyResized = true
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResizeMove(e) {
  if (!resizingCol) return
  const delta = e.clientX - resizeStartX
  const minWidth = COL_MIN_WIDTHS[resizingCol] || 50
  colWidths.value[resizingCol] = Math.max(minWidth, resizeStartWidth + delta)
}

function onResizeEnd() {
  resizingCol = null
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const containerRef = ref(null)
const scrollTop = ref(0)
const containerHeight = ref(600)

// 拖拽状态
const dragFromIndex = ref(-1)
const dragOverIndex = ref(-1)

const totalHeight = computed(() => props.symbols.length * ROW_HEIGHT)

const startIndex = computed(() => {
  const start = Math.floor(scrollTop.value / ROW_HEIGHT) - BUFFER_COUNT
  return Math.max(0, start)
})

const endIndex = computed(() => {
  const visibleCount = Math.ceil(containerHeight.value / ROW_HEIGHT)
  const end = startIndex.value + visibleCount + BUFFER_COUNT * 2
  return Math.min(props.symbols.length, end)
})

const offsetY = computed(() => startIndex.value * ROW_HEIGHT)

const visibleItems = computed(() => {
  return props.symbols.slice(startIndex.value, endIndex.value).map((item, i) => ({
    ...item,
    _index: startIndex.value + i
  }))
})

// ==================== 搜索高亮 ====================

function highlight(text) {
  if (!text || !props.searchQuery) return text
  const q = props.searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`(${q})`, 'gi')
  return text.replace(re, '<mark class="hl">$1</mark>')
}

// ==================== 价格/涨跌幅 ====================

function formatPrice(price) {
  if (price == null || price === undefined) return '-'
  return Number(price).toFixed(2)
}

function formatChange(pct) {
  if (pct == null || pct === undefined) return '-'
  const v = Number(pct)
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

function priceClass(item) {
  if (item.change_percent == null) return ''
  return item.change_percent > 0 ? 'price-up' : item.change_percent < 0 ? 'price-down' : ''
}

function changeClass(item) {
  if (item.change_percent == null) return ''
  return item.change_percent > 0 ? 'change-up' : item.change_percent < 0 ? 'change-down' : ''
}

// ==================== 拖拽排序 ====================

function onDragStart(e, index) {
  if (!isWatchlist.value) return
  dragFromIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(index))
}

function onDragOver(e, index) {
  if (!isWatchlist.value || dragFromIndex.value < 0) return
  dragOverIndex.value = index
}

function onDragLeave() {
  dragOverIndex.value = -1
}

function onDrop(e, toIndex) {
  if (!isWatchlist.value || dragFromIndex.value < 0) return
  dragOverIndex.value = -1
  const fromIndex = dragFromIndex.value
  if (fromIndex !== toIndex) {
    emit('reorder', { from: fromIndex, to: toIndex })
  }
  dragFromIndex.value = -1
}

function onDragEnd() {
  dragFromIndex.value = -1
  dragOverIndex.value = -1
}

// ==================== 滚动 ====================

function onScroll() {
  if (containerRef.value) {
    scrollTop.value = containerRef.value.scrollTop
  }
}

function updateContainerHeight() {
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight - 28
  }
}

let resizeObserver = null

onMounted(() => {
  updateContainerHeight()
  initColWidths()
  resizeObserver = new ResizeObserver(() => {
    updateContainerHeight()
    // 仅在用户未手动拖拽过时自适应
    if (!hasManuallyResized) initColWidths()
  })
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
})

watch(() => props.activeMarketType, () => {
  nextTick(() => {
    if (containerRef.value) {
      containerRef.value.scrollTop = 0
      scrollTop.value = 0
    }
  })
})
</script>

<style scoped>
.symbol-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.symbol-list::-webkit-scrollbar {
  width: 8px;
}

.symbol-list::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.symbol-list::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

.symbol-list::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.list-header {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  font-size: 11px;
  color: #888;
  border-bottom: 1px solid #333;
  background: #252526;
  position: sticky;
  top: 0;
  z-index: 1;
}

.list-header > span {
  border-right: 1px solid #3e3e3e;
  padding-left: 8px;
  padding-right: 8px;
  white-space: nowrap;
  overflow: hidden;
}

.list-header > span:first-child {
  padding-left: 0;
}

.list-header > span:last-child {
  border-right: none;
}

.virtual-list {
  position: relative;
}

.virtual-list-viewport {
  will-change: transform;
}

.symbol-row {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}

.symbol-row:hover {
  background: #2a2d2e;
}

.symbol-row-alt {
  background: #1f1f1f;
}

.symbol-row-alt:hover {
  background: #2a2d2e;
}

.symbol-row.drag-over {
  border-top: 2px solid #0e639c;
}

.col-drag {
  width: 20px;
  flex-shrink: 0;
  text-align: center;
  color: #555;
  cursor: grab;
  font-size: 12px;
  user-select: none;
}

.col-drag:active {
  cursor: grabbing;
}

.col-symbol {
  flex-shrink: 0;
  position: relative;
  padding-left: 0;
}

.col-name {
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #aaa;
  position: relative;
  padding-left: 8px;
}

.col-price {
  flex-shrink: 0;
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #aaa;
  position: relative;
  padding-left: 8px;
}

.col-change {
  flex: 1;
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #aaa;
  padding-left: 8px;
}

.col-resizer {
  position: absolute;
  top: 0;
  right: -1px;
  width: 5px;
  height: 100%;
  cursor: col-resize;
  z-index: 2;
  background: transparent;
}

.col-resizer:hover,
.col-resizer:active {
  background: #0e639c;
}

/* 涨跌颜色 (A股惯例: 红涨绿跌) */
.price-up { color: #ef4444; }
.price-down { color: #22c55e; }
.change-up { color: #ef4444; }
.change-down { color: #22c55e; }

.symbol-code {
  color: #ddd;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

/* 搜索高亮 */
:deep(.hl) {
  background: #806d00;
  color: #fff;
  padding: 0 1px;
  border-radius: 2px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 12px;
  color: #888;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #333;
  border-top-color: #0e639c;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 8px;
  color: #666;
}

.empty-icon {
  font-size: 32px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
