<template>
  <div class="session-list">
    <div class="session-list__header">
      <span>历史会话</span>
      <button class="session-close-btn" @click="$emit('close')">✕</button>
    </div>
    <div class="session-list__search">
      <input
        v-model="searchText"
        type="text"
        class="session-search-input"
        placeholder="搜索会话..."
      />
    </div>
    <div class="session-list__items">
      <div
        v-for="session in filteredSessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === currentSessionId }"
        @click="$emit('switch', session.id)"
      >
        <div class="session-item__title">{{ session.title || '新对话' }}</div>
        <div class="session-item__meta">
          <span>{{ formatDate(session.updated_at) }}</span>
          <span>{{ session.message_count }} 条</span>
        </div>
        <button class="session-item__delete" title="删除" @click.stop="$emit('delete', session.id)">×</button>
      </div>
      <div v-if="filteredSessions.length === 0" class="session-list__empty">
        暂无会话
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ChatSession } from '../../service/chatService'

const props = defineProps<{
  sessions: ChatSession[]
  currentSessionId: string | null
}>()

defineEmits<{
  'close': []
  'switch': [sessionId: string]
  'delete': [sessionId: string]
}>()

const searchText = ref('')

const filteredSessions = computed(() => {
  if (!searchText.value) return props.sessions
  const q = searchText.value.toLowerCase()
  return props.sessions.filter(s => (s.title || '').toLowerCase().includes(q))
})

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}分钟前`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}小时前`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.session-list {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #1e1e1e;
  z-index: 10;
  display: flex;
  flex-direction: column;
}

.session-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #333;
  font-size: 13px;
  color: #ccc;
}

.session-close-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}

.session-close-btn:hover {
  background: #333;
  color: #fff;
}

.session-list__search {
  padding: 8px 12px;
}

.session-search-input {
  width: 100%;
  background: #252525;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  padding: 6px 10px;
  color: #e0e0e0;
  font-size: 12px;
  outline: none;
}

.session-search-input:focus {
  border-color: #0e639c;
}

.session-list__items {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.session-item {
  position: relative;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;
}

.session-item:hover {
  background: #2a2a2a;
}

.session-item.active {
  background: #1a3a5c;
}

.session-item__title {
  font-size: 12px;
  color: #ddd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 20px;
}

.session-item__meta {
  display: flex;
  gap: 8px;
  font-size: 10px;
  color: #777;
  margin-top: 3px;
}

.session-item__delete {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.session-item:hover .session-item__delete {
  opacity: 1;
}

.session-item__delete:hover {
  background: #a83232;
  color: #fff;
}

.session-list__empty {
  text-align: center;
  color: #666;
  font-size: 12px;
  padding: 20px;
}
</style>
