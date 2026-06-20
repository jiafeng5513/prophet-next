<template>
  <div class="score-gauge">
    <svg viewBox="0 0 120 120" class="gauge-svg">
      <circle cx="60" cy="60" r="50" fill="none" stroke="#2d2d2d" stroke-width="8" />
      <circle
        cx="60" cy="60" r="50"
        fill="none"
        :stroke="color"
        stroke-width="8"
        stroke-linecap="round"
        :stroke-dasharray="dashArray"
        transform="rotate(-90 60 60)"
        class="gauge-arc"
      />
    </svg>
    <div class="gauge-center">
      <span class="gauge-value" :style="{ color }">{{ score ?? '--' }}</span>
      <span class="gauge-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: null },
  label: { type: String, default: '情绪评分' }
})

const circumference = 2 * Math.PI * 50

const color = computed(() => {
  const s = props.score
  if (s == null) return '#666'
  if (s >= 80) return '#2ea043'
  if (s >= 60) return '#3fb950'
  if (s >= 40) return '#d29922'
  if (s >= 25) return '#f0883e'
  return '#da3633'
})

const dashArray = computed(() => {
  if (props.score == null) return `0 ${circumference}`
  const filled = (Math.min(100, Math.max(0, props.score)) / 100) * circumference
  return `${filled} ${circumference}`
})
</script>

<style scoped>
.score-gauge {
  position: relative;
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}
.gauge-svg {
  width: 100%;
  height: 100%;
}
.gauge-arc {
  transition: stroke-dasharray 0.8s ease;
}
.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.gauge-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}
.gauge-label {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}
</style>
