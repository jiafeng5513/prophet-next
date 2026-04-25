<template>
  <div class="advice-badges">
    <span class="badge" :class="adviceClass" v-if="advice">{{ advice }}</span>
    <span class="badge trend-badge" :class="trendClass" v-if="trend">{{ trend }}</span>
    <span class="badge confidence-badge" v-if="confidence">{{ confidence }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  advice: { type: String, default: '' },
  trend: { type: String, default: '' },
  confidence: { type: String, default: '' }
})

const adviceClass = computed(() => {
  const a = (props.advice || '').toLowerCase()
  if (a.includes('买') || a.includes('建仓') || a.includes('buy')) return 'buy'
  if (a.includes('卖') || a.includes('减仓') || a.includes('sell') || a.includes('清仓')) return 'sell'
  if (a.includes('持有') || a.includes('hold')) return 'hold'
  return 'neutral'
})

const trendClass = computed(() => {
  const t = (props.trend || '').toLowerCase()
  if (t.includes('多') || t.includes('涨') || t.includes('bull')) return 'bullish'
  if (t.includes('空') || t.includes('跌') || t.includes('bear')) return 'bearish'
  return 'neutral-trend'
})
</script>

<style scoped>
.advice-badges {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}
.badge {
  padding: 4px 14px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.badge.buy { background: rgba(46,160,67,0.15); color: #3fb950; border: 1px solid rgba(46,160,67,0.3); }
.badge.sell { background: rgba(218,54,51,0.15); color: #f85149; border: 1px solid rgba(218,54,51,0.3); }
.badge.hold { background: rgba(74,158,255,0.15); color: #4a9eff; border: 1px solid rgba(74,158,255,0.3); }
.badge.neutral { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.badge.bullish { background: rgba(248,81,73,0.1); color: #f85149; border: 1px solid rgba(248,81,73,0.2); }
.badge.bearish { background: rgba(63,185,80,0.1); color: #3fb950; border: 1px solid rgba(63,185,80,0.2); }
.badge.neutral-trend { background: rgba(210,153,34,0.1); color: #d29922; border: 1px solid rgba(210,153,34,0.2); }
.confidence-badge { background: #2d2d2d; color: #aaa; border: 1px solid #444; }
</style>
