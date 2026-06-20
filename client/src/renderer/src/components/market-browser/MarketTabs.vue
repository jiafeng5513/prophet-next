<template>
  <div class="market-tabs">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="tab-btn"
      :class="{ active: modelValue === tab.key }"
      @click="$emit('update:modelValue', tab.key)"
    >
      <span class="tab-icon">{{ tab.icon }}</span>
      <span class="tab-label">{{ tab.label }}</span>
      <span v-if="tab.count != null" class="tab-count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  tabs: {
    type: Array,
    required: true
    // Each tab: { key, label, icon, count? }
  },
  modelValue: {
    type: String,
    required: true
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.market-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 12px;
  background: #252526;
  border-bottom: 1px solid #3a3a3c;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: #999;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
  white-space: nowrap;
}

.tab-btn:hover {
  color: #e0e0e0;
}

.tab-btn.active {
  color: #fff;
  border-bottom-color: #4fc3f7;
}

.tab-icon {
  font-size: 14px;
}

.tab-count {
  font-size: 11px;
  color: #777;
  background: #333;
  padding: 1px 5px;
  border-radius: 8px;
}

.tab-btn.active .tab-count {
  color: #4fc3f7;
  background: #1a3a4a;
}
</style>
