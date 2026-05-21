<template>
  <div class="tool-call-card" :class="`tool-call-card--${tool.status}`">
    <div class="tool-call-card__header">
      <span class="tool-icon">{{ statusIcon }}</span>
      <span class="tool-name">{{ tool.name }}</span>
      <span v-if="tool.duration" class="tool-duration">{{ tool.duration.toFixed(1) }}s</span>
      <span v-if="tool.status === 'running'" class="tool-spinner">⟳</span>
    </div>
    <div v-if="tool.result && expanded" class="tool-call-card__result">
      <pre>{{ truncatedResult }}</pre>
    </div>
    <button v-if="tool.result" class="tool-expand-btn" @click="expanded = !expanded">
      {{ expanded ? '收起' : '查看结果' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCallInfo } from '../../service/chatService'

const props = defineProps<{
  tool: ToolCallInfo
}>()

const expanded = ref(false)

const statusIcon = computed(() => {
  switch (props.tool.status) {
    case 'done': return '✓'
    case 'running': return '⏳'
    case 'error': return '✗'
    default: return '○'
  }
})

const truncatedResult = computed(() => {
  const r = props.tool.result || ''
  return r.length > 500 ? r.slice(0, 500) + '...' : r
})
</script>

<style scoped>
.tool-call-card {
  background: #1a2634;
  border-radius: 8px;
  border-left: 3px solid #555;
  margin-bottom: 6px;
  overflow: hidden;
}

.tool-call-card--done {
  border-left-color: #4ec9b0;
}

.tool-call-card--running {
  border-left-color: #dcdcaa;
}

.tool-call-card--error {
  border-left-color: #f48771;
}

.tool-call-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
}

.tool-icon {
  font-size: 12px;
}

.tool-call-card--done .tool-icon { color: #4ec9b0; }
.tool-call-card--running .tool-icon { color: #dcdcaa; }
.tool-call-card--error .tool-icon { color: #f48771; }

.tool-name {
  color: #b8d4e8;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
}

.tool-duration {
  margin-left: auto;
  color: #666;
  font-size: 10px;
}

.tool-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tool-call-card__result {
  padding: 0 12px 8px;
}

.tool-call-card__result pre {
  background: #0d1117;
  border-radius: 4px;
  padding: 8px;
  font-size: 10px;
  color: #aaa;
  overflow-x: auto;
  max-height: 150px;
  margin: 0;
}

.tool-expand-btn {
  width: 100%;
  background: none;
  border: none;
  border-top: 1px solid #2a3a4a;
  color: #7ec8e3;
  font-size: 10px;
  padding: 5px;
  cursor: pointer;
}

.tool-expand-btn:hover {
  background: rgba(126, 200, 227, 0.1);
}
</style>
