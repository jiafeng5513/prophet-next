<template>
  <div class="price-card">
    <div class="price-main" :class="priceClass">
      <span class="price-value">{{ formattedPrice }}</span>
      <span class="price-change" v-if="changePct != null">
        {{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}%
      </span>
    </div>
    <div class="price-label">当前价</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  price: { type: Number, default: null },
  changePct: { type: Number, default: null }
})

const formattedPrice = computed(() => {
  if (props.price == null) return '--'
  return '¥' + props.price.toFixed(2)
})

const priceClass = computed(() => {
  if (props.changePct == null) return ''
  return props.changePct >= 0 ? 'up' : 'down'
})
</script>

<style scoped>
.price-card {
  text-align: center;
}
.price-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.price-value {
  font-size: 28px;
  font-weight: 700;
  color: #e0e0e0;
}
.price-change {
  font-size: 15px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.price-main.up .price-value { color: #f85149; }
.price-main.up .price-change { color: #f85149; background: rgba(248,81,73,0.1); }
.price-main.down .price-value { color: #3fb950; }
.price-main.down .price-change { color: #3fb950; background: rgba(63,185,80,0.1); }
.price-label {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}
</style>
