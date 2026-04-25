<template>
  <div class="strategy-section" v-if="hasContent">
    <h3 class="section-title">🎯 策略点位</h3>
    <div class="strategy-grid">
      <div class="strategy-card buy1" v-if="strategy.ideal_buy">
        <span class="card-label">理想买入</span>
        <span class="card-value">{{ strategy.ideal_buy }}</span>
      </div>
      <div class="strategy-card buy2" v-if="strategy.secondary_buy">
        <span class="card-label">第二买入</span>
        <span class="card-value">{{ strategy.secondary_buy }}</span>
      </div>
      <div class="strategy-card stop" v-if="strategy.stop_loss">
        <span class="card-label">止损位</span>
        <span class="card-value">{{ strategy.stop_loss }}</span>
      </div>
      <div class="strategy-card profit" v-if="strategy.take_profit">
        <span class="card-label">止盈位</span>
        <span class="card-value">{{ strategy.take_profit }}</span>
      </div>
    </div>

    <div class="position-info" v-if="battlePlan.position_strategy">
      <div class="position-item" v-if="battlePlan.position_strategy.suggested_position">
        <span class="pos-label">建议仓位</span>
        <span class="pos-value">{{ battlePlan.position_strategy.suggested_position }}</span>
      </div>
      <div class="position-item" v-if="battlePlan.position_strategy.entry_plan">
        <span class="pos-label">入场计划</span>
        <span class="pos-value">{{ battlePlan.position_strategy.entry_plan }}</span>
      </div>
      <div class="position-item" v-if="battlePlan.position_strategy.risk_control">
        <span class="pos-label">风控策略</span>
        <span class="pos-value">{{ battlePlan.position_strategy.risk_control }}</span>
      </div>
    </div>

    <div class="action-checklist" v-if="battlePlan.action_checklist && battlePlan.action_checklist.length">
      <h4>✅ 行动清单</h4>
      <ul>
        <li v-for="(item, i) in battlePlan.action_checklist" :key="i">{{ item }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  strategy: { type: Object, default: () => ({}) },
  battlePlan: { type: Object, default: () => ({}) }
})

const hasContent = computed(() => {
  const s = props.strategy
  return s.ideal_buy || s.secondary_buy || s.stop_loss || s.take_profit
})
</script>

<style scoped>
.strategy-section {
  margin: 20px 0;
}
.section-title {
  font-size: 16px;
  color: #e0e0e0;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2a2a;
}
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.strategy-card {
  background: #252526;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  border-bottom: 3px solid transparent;
  transition: transform 0.15s, box-shadow 0.15s;
}
.strategy-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.strategy-card.buy1 { border-bottom-color: #2ea043; }
.strategy-card.buy2 { border-bottom-color: #4a9eff; }
.strategy-card.stop { border-bottom-color: #da3633; }
.strategy-card.profit { border-bottom-color: #a371f7; }
.card-label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}
.card-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #e0e0e0;
}
.position-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #252526;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.position-item {
  display: flex;
  gap: 12px;
  font-size: 13px;
}
.pos-label {
  color: #888;
  min-width: 70px;
  flex-shrink: 0;
}
.pos-value {
  color: #d4d4d4;
}
.action-checklist {
  background: #252526;
  border-radius: 8px;
  padding: 14px 16px;
}
.action-checklist h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #e0e0e0;
}
.action-checklist ul {
  margin: 0;
  padding-left: 20px;
}
.action-checklist li {
  font-size: 13px;
  color: #d4d4d4;
  margin: 4px 0;
}
.action-checklist li::marker {
  color: #3fb950;
}
@media (max-width: 600px) {
  .strategy-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
