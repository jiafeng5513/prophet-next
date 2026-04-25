<template>
  <div class="collapsible-panel" :class="{ expanded: isOpen }">
    <div class="panel-header" @click="toggle">
      <span class="panel-arrow">{{ isOpen ? '▾' : '▸' }}</span>
      <span class="panel-title">{{ title }}</span>
    </div>
    <div class="panel-body" v-show="isOpen">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  defaultOpen: { type: Boolean, default: true }
})

const isOpen = ref(props.defaultOpen)

function toggle() {
  isOpen.value = !isOpen.value
}
</script>

<style scoped>
.collapsible-panel {
  margin-bottom: 4px;
  border-radius: 6px;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #252526;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.panel-header:hover {
  background: #2a2d2e;
}
.panel-arrow {
  font-size: 12px;
  color: #888;
  width: 14px;
  text-align: center;
}
.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
}
.panel-body {
  padding: 12px 16px;
  background: #1e1e1e;
}
</style>
