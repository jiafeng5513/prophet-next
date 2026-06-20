<template>
  <div class="thinking-block" :class="{ expanded }">
    <div class="thinking-block__header" @click="expanded = !expanded">
      <span class="thinking-icon">💭</span>
      <span class="thinking-label">思考过程</span>
      <span class="thinking-toggle">{{ expanded ? '▼' : '▶' }}</span>
    </div>
    <div v-if="expanded" class="thinking-block__content">
      {{ content }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  content: string
}>()

const expanded = ref(false)
</script>

<style scoped>
.thinking-block {
  background: #1a1a2e;
  border-radius: 8px;
  margin-bottom: 8px;
  border: 1px solid #2a2a4a;
}

.thinking-block__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: #888;
  transition: color 0.15s;
}

.thinking-block__header:hover {
  color: #bbb;
}

.thinking-icon {
  font-size: 14px;
}

.thinking-label {
  flex: 1;
  font-style: italic;
}

.thinking-toggle {
  font-size: 10px;
}

.thinking-block__content {
  padding: 0 12px 10px;
  font-size: 11px;
  color: #999;
  line-height: 1.5;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}
</style>
