<template>
  <div class="analysis-radar">
    <div class="radar-title">多维评分</div>
    <svg :viewBox="`0 0 ${size} ${size}`" class="radar-svg">
      <!-- 背景网格 -->
      <polygon
        v-for="level in gridLevels"
        :key="level"
        :points="gridPoints(level)"
        class="radar-grid"
      />
      <!-- 轴线 -->
      <line
        v-for="(_, i) in dimensions"
        :key="'axis-' + i"
        :x1="center"
        :y1="center"
        :x2="axisEnd(i).x"
        :y2="axisEnd(i).y"
        class="radar-axis"
      />
      <!-- 数据区域 -->
      <polygon :points="dataPoints" class="radar-area" />
      <circle
        v-for="(pt, i) in dataPointsArray"
        :key="'dot-' + i"
        :cx="pt.x"
        :cy="pt.y"
        r="3"
        class="radar-dot"
      />
      <!-- 标签 -->
      <text
        v-for="(dim, i) in dimensions"
        :key="'label-' + i"
        :x="labelPos(i).x"
        :y="labelPos(i).y"
        class="radar-label"
        text-anchor="middle"
        dominant-baseline="central"
      >{{ dim.label }} {{ dim.value }}</text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface RadarDimension {
  key: string
  label: string
  value: number // 0-100
}

const props = withDefaults(defineProps<{
  dimensions: RadarDimension[]
}>(), {
  dimensions: () => []
})

const size = 220
const center = size / 2
const radius = 80
const gridLevels = [0.25, 0.5, 0.75, 1.0]

function polarToCartesian(angle: number, r: number) {
  const rad = (angle - 90) * (Math.PI / 180)
  return {
    x: center + r * Math.cos(rad),
    y: center + r * Math.sin(rad)
  }
}

function angleForIndex(i: number) {
  return (360 / props.dimensions.length) * i
}

function axisEnd(i: number) {
  return polarToCartesian(angleForIndex(i), radius)
}

function labelPos(i: number) {
  return polarToCartesian(angleForIndex(i), radius + 18)
}

function gridPoints(level: number) {
  return props.dimensions
    .map((_, i) => {
      const pt = polarToCartesian(angleForIndex(i), radius * level)
      return `${pt.x},${pt.y}`
    })
    .join(' ')
}

const dataPointsArray = computed(() =>
  props.dimensions.map((dim, i) => {
    const val = Math.min(100, Math.max(0, dim.value)) / 100
    return polarToCartesian(angleForIndex(i), radius * val)
  })
)

const dataPoints = computed(() =>
  dataPointsArray.value.map(pt => `${pt.x},${pt.y}`).join(' ')
)
</script>

<style scoped>
.analysis-radar {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background: #1e2a36;
  border-radius: 8px;
}

.radar-title {
  font-size: 12px;
  font-weight: 600;
  color: #8bb8d4;
  margin-bottom: 4px;
}

.radar-svg {
  width: 100%;
  max-width: 220px;
  height: auto;
}

.radar-grid {
  fill: none;
  stroke: #2a3f52;
  stroke-width: 0.5;
}

.radar-axis {
  stroke: #2a3f52;
  stroke-width: 0.5;
}

.radar-area {
  fill: rgba(74, 158, 255, 0.2);
  stroke: #4a9eff;
  stroke-width: 1.5;
}

.radar-dot {
  fill: #4a9eff;
}

.radar-label {
  font-size: 9px;
  fill: #aaa;
}
</style>
