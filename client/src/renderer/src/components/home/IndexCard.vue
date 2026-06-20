<template>
  <div class="index-card" :class="changeClass" @click="$emit('click', index)">
    <div class="card-header">
      <span class="card-name">{{ index.name }}</span>
      <span class="card-code">{{ index.symbol }}</span>
    </div>
    <div class="card-price">{{ formatPrice(index.price) }}</div>
    <div class="card-change">
      <span class="change-pct">{{ formatPercent(index.change_percent) }}</span>
      <span class="change-val">{{ formatChange(index.change) }}</span>
    </div>
    <canvas ref="sparkCanvas" class="card-sparkline" width="120" height="32"></canvas>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  index: {
    type: Object,
    required: true
  }
})

defineEmits(['click'])

const sparkCanvas = ref(null)

const changeClass = computed(() => {
  const pct = props.index.change_percent
  if (pct > 0) return 'is-up'
  if (pct < 0) return 'is-down'
  return 'is-flat'
})

function formatPrice(price) {
  if (price == null) return '--'
  if (price >= 10000) return price.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  return price.toFixed(2)
}

function formatPercent(pct) {
  if (pct == null) return '--'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

function formatChange(change) {
  if (change == null) return ''
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}`
}

function drawSparkline(data) {
  const canvas = sparkCanvas.value
  if (!canvas || !data || data.length < 2) return

  const ctx = canvas.getContext('2d')
  const w = canvas.width
  const h = canvas.height
  ctx.clearRect(0, 0, w, h)

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const color = props.index.change_percent >= 0 ? '#26a69a' : '#ef5350'
  ctx.strokeStyle = color
  ctx.lineWidth = 1.5
  ctx.beginPath()

  data.forEach((val, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - ((val - min) / range) * (h - 4) - 2
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.stroke()
}

watch(() => props.index.sparkline, (data) => {
  nextTick(() => drawSparkline(data))
})

onMounted(() => {
  if (props.index.sparkline) {
    drawSparkline(props.index.sparkline)
  }
})
</script>

<style scoped>
.index-card {
  background: #2a2a2c;
  border: 1px solid #3a3a3c;
  border-radius: 8px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 160px;
}

.index-card:hover {
  background: #333335;
  border-color: #505052;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-name {
  font-size: 13px;
  color: #e0e0e0;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-code {
  font-size: 11px;
  color: #888;
}

.card-price {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 4px 0 2px;
}

.card-change {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.change-pct {
  font-weight: 500;
}

.change-val {
  color: #999;
}

.is-up .card-price,
.is-up .change-pct {
  color: #26a69a;
}

.is-down .card-price,
.is-down .change-pct {
  color: #ef5350;
}

.is-flat .card-price {
  color: #e0e0e0;
}

.is-flat .change-pct {
  color: #999;
}

.card-sparkline {
  margin-top: 4px;
  width: 100%;
  height: 32px;
}
</style>
