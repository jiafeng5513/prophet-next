<template>
  <div class="news-timeline">
    <!-- 加载中 -->
    <div v-if="loading && groups.length === 0" class="timeline-loading">
      <div class="loading-spinner"></div>
      <span>加载新闻中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="groups.length === 0" class="timeline-empty">
      <div class="empty-icon">📰</div>
      <p>暂无新闻数据</p>
      <p class="empty-hint">点击右上角刷新按钮获取最新新闻</p>
    </div>

    <!-- 时间线列表 -->
    <div v-else ref="scrollContainer" class="timeline-list" @scroll="onScroll">
      <div v-for="group in groups" :key="group.date" class="timeline-group">
        <div class="timeline-date">{{ formatDate(group.date) }}</div>
        <div
          v-for="item in group.items"
          :key="item.id"
          class="timeline-item"
          :class="{ active: item.id === selectedId }"
          @click="$emit('select', item)"
        >
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <div class="timeline-title">{{ item.title }}</div>
            <div class="timeline-meta">
              <span v-if="item.source" class="timeline-source">{{ item.source }}</span>
              <span v-if="item.code" class="timeline-stock">{{ item.name || item.code }}</span>
              <span class="timeline-time">{{ formatTime(item.published_date) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部加载更多 -->
      <div v-if="loading" class="timeline-load-more">
        <div class="loading-spinner small"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  groups: { type: Array, default: () => [] },
  selectedId: { type: Number, default: null },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['select', 'load-more'])

const scrollContainer = ref(null)

function onScroll() {
  const el = scrollContainer.value
  if (!el) return
  // 距离底部 100px 时触发加载更多
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 100) {
    emit('load-more')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const today = new Date()
  const date = new Date(dateStr)
  const todayStr = today.toISOString().slice(0, 10)
  const yesterdayStr = new Date(today.getTime() - 86400000).toISOString().slice(0, 10)

  if (dateStr === todayStr) return '今天'
  if (dateStr === yesterdayStr) return '昨天'

  const month = date.getMonth() + 1
  const day = date.getDate()
  return `${month}月${day}日`
}

function formatTime(dateTimeStr) {
  if (!dateTimeStr) return ''
  // dateTimeStr: "2026-04-25 10:30:00"
  const parts = dateTimeStr.split(' ')
  if (parts.length >= 2) return parts[1].slice(0, 5)
  return ''
}
</script>

<style scoped>
.news-timeline {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.timeline-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 20px;
}

.timeline-group {
  margin-bottom: 4px;
}

.timeline-date {
  font-size: 12px;
  color: #999;
  padding: 12px 0 6px 24px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  padding: 10px 12px 10px 8px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
  position: relative;
}

.timeline-item:hover {
  background: #2a2d2e;
}

.timeline-item.active {
  background: #37373d;
}

.timeline-item.active .timeline-dot {
  background: #fff;
  box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.3);
}

.timeline-dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
  background: #4a9eff;
  margin-top: 6px;
  margin-right: 12px;
  position: relative;
}

/* 时间线竖线 */
.timeline-item:not(:last-child) .timeline-dot::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 10px;
  width: 2px;
  height: calc(100% + 14px);
  background: #333;
}

.timeline-content {
  flex: 1;
  min-width: 0;
}

.timeline-title {
  font-size: 13px;
  line-height: 1.5;
  color: #e0e0e0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.timeline-item.active .timeline-title {
  color: #fff;
}

.timeline-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: #777;
}

.timeline-source {
  color: #4a9eff;
}

.timeline-stock {
  background: #2a2d2e;
  padding: 1px 6px;
  border-radius: 3px;
  color: #aaa;
  font-size: 10px;
}

.timeline-time {
  margin-left: auto;
  white-space: nowrap;
}

/* 加载和空状态 */
.timeline-loading,
.timeline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #777;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.empty-hint {
  font-size: 12px;
  color: #555;
}

.timeline-load-more {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #333;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner.small {
  width: 16px;
  height: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
