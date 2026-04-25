<template>
  <div class="report-overview">
    <div class="overview-row">
      <ScoreGauge :score="sentimentScore" :label="sentimentLabel || '情绪评分'" />
      <PriceCard :price="currentPrice" :change-pct="changePct" />
      <AdviceBadge :advice="operationAdvice" :trend="trendPrediction" :confidence="confidence" />
    </div>

    <div class="conclusion-block" v-if="conclusion">
      <div class="signal-line" v-if="conclusion.one_sentence">
        <span class="signal-type" :class="signalClass">{{ conclusion.signal_type || 'INFO' }}</span>
        <span class="signal-text">{{ conclusion.one_sentence }}</span>
      </div>
      <div class="sensitivity" v-if="conclusion.time_sensitivity">
        <span class="sensitivity-label">时效性：</span>{{ conclusion.time_sensitivity }}
      </div>
      <div class="position-advice" v-if="conclusion.position_advice">
        <div v-if="conclusion.position_advice.no_position" class="advice-line">
          <span class="advice-tag empty">空仓</span>{{ conclusion.position_advice.no_position }}
        </div>
        <div v-if="conclusion.position_advice.has_position" class="advice-line">
          <span class="advice-tag held">持仓</span>{{ conclusion.position_advice.has_position }}
        </div>
      </div>
    </div>

    <div class="summary-text" v-if="analysisSummary">
      <p>{{ analysisSummary }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ScoreGauge from './ScoreGauge.vue'
import PriceCard from './PriceCard.vue'
import AdviceBadge from './AdviceBadge.vue'

const props = defineProps({
  meta: { type: Object, default: () => ({}) },
  summary: { type: Object, default: () => ({}) },
  conclusion: { type: Object, default: null }
})

const currentPrice = computed(() => props.meta.current_price)
const changePct = computed(() => props.meta.change_pct)
const sentimentScore = computed(() => props.summary.sentiment_score)
const sentimentLabel = computed(() => props.summary.sentiment_label)
const operationAdvice = computed(() => props.summary.operation_advice)
const trendPrediction = computed(() => props.summary.trend_prediction)
const confidence = computed(() => props.summary.sentiment_label)
const analysisSummary = computed(() => props.summary.analysis_summary)

const signalClass = computed(() => {
  const s = (props.conclusion?.signal_type || '').toUpperCase()
  if (s === 'BUY' || s.includes('买')) return 'buy'
  if (s === 'SELL' || s.includes('卖')) return 'sell'
  if (s === 'HOLD' || s.includes('持')) return 'hold'
  return 'info'
})
</script>

<style scoped>
.report-overview {
  margin-bottom: 24px;
}
.overview-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  background: #252526;
  border-radius: 10px;
  margin-bottom: 16px;
}
.conclusion-block {
  background: #252526;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
  border-left: 3px solid #4a9eff;
}
.signal-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.signal-type {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.signal-type.buy { background: rgba(46,160,67,0.15); color: #3fb950; }
.signal-type.sell { background: rgba(218,54,51,0.15); color: #f85149; }
.signal-type.hold { background: rgba(74,158,255,0.15); color: #4a9eff; }
.signal-type.info { background: rgba(210,153,34,0.15); color: #d29922; }
.signal-text {
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
}
.sensitivity {
  font-size: 12px;
  color: #888;
  margin-bottom: 10px;
}
.sensitivity-label {
  color: #666;
}
.position-advice {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.advice-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  color: #d4d4d4;
}
.advice-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}
.advice-tag.empty { background: #0e3a5c; color: #4a9eff; }
.advice-tag.held { background: #1a3a1a; color: #3fb950; }
.summary-text {
  font-size: 14px;
  color: #bbb;
  line-height: 1.6;
  padding: 0 4px;
}
.summary-text p {
  margin: 0;
}
</style>
