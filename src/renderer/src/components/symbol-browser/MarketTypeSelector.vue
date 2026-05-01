<template>
  <div class="market-type-selector">
    <button
      v-for="t in types"
      :key="t.type"
      :class="['type-btn', { active: t.type === active, disabled: !t.enabled }]"
      :disabled="!t.enabled"
      :title="t.enabled ? t.label : `${t.label} (暂不可用)`"
      @click="t.enabled && $emit('change', t.type)"
    >
      <span class="type-icon">{{ getIcon(t.type) }}</span>
      <span class="type-label">{{ t.label }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  types: { type: Array, default: () => [] },
  active: { type: String, default: '' }
})

defineEmits(['change'])

const iconMap = {
  crypto: '₿',
  cn_stock: '沪',
  cn_etf: 'E',
  cn_futures: '期',
  hk_stock: '港',
  us_stock: '美'
}

function getIcon(type) {
  return iconMap[type] || '●'
}
</script>

<style scoped>
.market-type-selector {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.type-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid #444;
  border-radius: 4px;
  background: transparent;
  color: #aaa;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.type-btn:hover:not(.disabled) {
  background: #333;
  color: #ddd;
  border-color: #555;
}

.type-btn.active {
  background: #0e639c;
  color: #fff;
  border-color: #1177bb;
}

.type-btn.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.type-icon {
  font-weight: bold;
  font-size: 11px;
}

.type-label {
  font-size: 12px;
}
</style>
