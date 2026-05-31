<template>
  <div class="data-table-wrapper" ref="wrapperRef">
    <!-- 表头 -->
    <div class="table-header" ref="headerRef">
      <div class="header-row">
        <div
          v-for="col in visibleColumns"
          :key="col.key"
          class="header-cell"
          :class="{ sortable: col.sortable, sorted: sortKey === col.key, sticky: col.sticky }"
          :style="{ width: col.width + 'px', minWidth: col.minWidth + 'px' }"
          @click="col.sortable && toggleSort(col.key)"
        >
          <span class="header-label">{{ col.label }}</span>
          <span v-if="col.sortable" class="sort-indicator">
            <svg v-if="sortKey === col.key && sortDir === 'asc'" width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <path d="M5 2L9 7H1z"/>
            </svg>
            <svg v-else-if="sortKey === col.key && sortDir === 'desc'" width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <path d="M5 8L1 3h8z"/>
            </svg>
            <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="currentColor" opacity="0.3">
              <path d="M5 2L8 5H2zM5 8L2 5h6z"/>
            </svg>
          </span>
        </div>
      </div>
    </div>

    <!-- 虚拟滚动表体 -->
    <div class="table-body" ref="bodyRef" @scroll="handleScroll">
      <div class="scroll-spacer" :style="{ height: totalHeight + 'px' }">
        <div class="visible-rows" :style="{ transform: `translateY(${offsetY}px)` }">
          <div
            v-for="row in visibleRows"
            :key="row._id || row.symbol"
            class="table-row"
            :class="{ 'row-hover': hoveredRow === row.symbol }"
            @mouseenter="hoveredRow = row.symbol"
            @mouseleave="hoveredRow = null"
            @dblclick="$emit('rowDblClick', row)"
            @contextmenu.prevent="$emit('rowContextMenu', $event, row)"
          >
            <div
              v-for="col in visibleColumns"
              :key="col.key"
              class="table-cell"
              :class="[col.align || 'left', getCellClass(col, row), { sticky: col.sticky }]"
              :style="{ width: col.width + 'px', minWidth: col.minWidth + 'px' }"
            >
              <template v-if="col.key === 'change_pct'">
                <span :class="getChangeClass(row[col.key])">{{ formatPercent(row[col.key]) }}</span>
              </template>
              <template v-else-if="col.type === 'number'">
                {{ formatNumber(row[col.key], col.decimals) }}
              </template>
              <template v-else-if="col.type === 'volume'">
                {{ formatVolume(row[col.key]) }}
              </template>
              <template v-else-if="col.type === 'marketCap'">
                {{ formatMarketCap(row[col.key]) }}
              </template>
              <template v-else>
                {{ row[col.key] ?? '--' }}
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="table-footer">
      <span class="footer-info">共 {{ totalRows }} 只</span>
      <span v-if="filteredCount !== totalRows" class="footer-info">已筛选 {{ filteredCount }} 只</span>
      <span v-if="updateTime" class="footer-time">刷新时间: {{ updateTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, required: true },
  totalRows: { type: Number, default: 0 },
  filteredCount: { type: Number, default: 0 },
  updateTime: { type: String, default: '' },
  rowHeight: { type: Number, default: 34 },
  bufferRows: { type: Number, default: 10 }
})

defineEmits(['rowDblClick', 'rowContextMenu', 'sort'])

const wrapperRef = ref(null)
const headerRef = ref(null)
const bodyRef = ref(null)
const hoveredRow = ref(null)
const sortKey = ref('')
const sortDir = ref('') // 'asc' | 'desc' | ''

const scrollTop = ref(0)
const containerHeight = ref(600)

const visibleColumns = computed(() => props.columns.filter(c => c.visible !== false))

// 排序后的数据
const sortedData = computed(() => {
  if (!sortKey.value || !sortDir.value) return props.data
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...props.data].sort((a, b) => {
    const va = a[key]
    const vb = b[key]
    if (va == null && vb == null) return 0
    if (va == null) return 1
    if (vb == null) return -1
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

// 虚拟滚动计算
const totalHeight = computed(() => sortedData.value.length * props.rowHeight)

const startIndex = computed(() => {
  return Math.max(0, Math.floor(scrollTop.value / props.rowHeight) - props.bufferRows)
})

const endIndex = computed(() => {
  const visibleCount = Math.ceil(containerHeight.value / props.rowHeight)
  return Math.min(sortedData.value.length, startIndex.value + visibleCount + props.bufferRows * 2)
})

const offsetY = computed(() => startIndex.value * props.rowHeight)

const visibleRows = computed(() => sortedData.value.slice(startIndex.value, endIndex.value))

function handleScroll() {
  if (bodyRef.value) {
    scrollTop.value = bodyRef.value.scrollTop
  }
}

function toggleSort(key) {
  if (sortKey.value === key) {
    if (sortDir.value === 'asc') sortDir.value = 'desc'
    else if (sortDir.value === 'desc') { sortKey.value = ''; sortDir.value = '' }
    else sortDir.value = 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc' // 默认降序
  }
}

function getChangeClass(val) {
  if (val > 0) return 'is-up'
  if (val < 0) return 'is-down'
  return ''
}

function getCellClass(col, row) {
  if (col.key === 'change_pct') return ''
  if (col.colorBySign && row[col.key] != null) {
    return row[col.key] > 0 ? 'is-up' : row[col.key] < 0 ? 'is-down' : ''
  }
  return ''
}

function formatPercent(val) {
  if (val == null) return '--'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatNumber(val, decimals = 2) {
  if (val == null) return '--'
  return val.toLocaleString('zh-CN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals })
}

function formatVolume(val) {
  if (val == null) return '--'
  if (val >= 100000000) return (val / 100000000).toFixed(2) + '亿'
  if (val >= 10000) return (val / 10000).toFixed(1) + '万'
  return val.toLocaleString()
}

function formatMarketCap(val) {
  if (val == null) return '--'
  if (val >= 100000000) return (val / 100000000).toFixed(0) + '亿'
  if (val >= 10000) return (val / 10000).toFixed(0) + '万'
  return val.toLocaleString()
}

let resizeObserver = null

onMounted(() => {
  if (bodyRef.value) {
    containerHeight.value = bodyRef.value.clientHeight
    resizeObserver = new ResizeObserver(() => {
      containerHeight.value = bodyRef.value?.clientHeight || 600
    })
    resizeObserver.observe(bodyRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  color: #e0e0e0;
  font-size: 13px;
}

.table-header {
  flex-shrink: 0;
  background: #252526;
  border-bottom: 1px solid #3a3a3c;
  overflow: hidden;
}

.header-row {
  display: flex;
  align-items: center;
}

.header-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  font-size: 12px;
  color: #999;
  font-weight: 500;
  user-select: none;
  flex-shrink: 0;
}

.header-cell.sortable {
  cursor: pointer;
}

.header-cell.sortable:hover {
  color: #e0e0e0;
}

.header-cell.sorted {
  color: #4fc3f7;
}

.header-cell.sticky {
  position: sticky;
  left: 0;
  background: #252526;
  z-index: 2;
}

.sort-indicator {
  display: flex;
  align-items: center;
}

.table-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
}

.scroll-spacer {
  position: relative;
}

.visible-rows {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}

.table-row {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #2a2a2c;
  transition: background 0.1s;
}

.table-row.row-hover {
  background: #2a2d30;
}

.table-cell {
  padding: 6px 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.table-cell.sticky {
  position: sticky;
  left: 0;
  background: #1e1e1e;
  z-index: 1;
}

.table-row.row-hover .table-cell.sticky {
  background: #2a2d30;
}

.table-cell.right {
  text-align: right;
}

.table-cell.center {
  text-align: center;
}

.is-up {
  color: #26a69a;
}

.is-down {
  color: #ef5350;
}

.table-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 6px 12px;
  background: #252526;
  border-top: 1px solid #3a3a3c;
  font-size: 12px;
  color: #888;
}

.footer-time {
  margin-left: auto;
}
</style>
