<template>
  <div class="dashboard-result">
    <div class="dashboard-result__header">
      <span class="dashboard-title">分析结论</span>
    </div>

    <div class="dashboard-result__body">
      <!-- 信号 + 置信度 -->
      <div class="dashboard-signal-row" v-if="dashboard.signal || dashboard.confidence != null">
        <div v-if="dashboard.signal" class="signal-badge" :class="`signal-badge--${dashboard.signal}`">
          {{ signalLabel(dashboard.signal) }}
        </div>
        <div v-if="dashboard.confidence != null" class="confidence-bar">
          <div class="confidence-fill" :style="{ width: (dashboard.confidence * 100) + '%' }"></div>
          <span class="confidence-text">{{ (dashboard.confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- 摘要 -->
      <div v-if="dashboard.summary" class="dashboard-summary">
        {{ dashboard.summary }}
      </div>

      <!-- 市场环境 -->
      <div v-if="dashboard.market_context" class="dashboard-section">
        <div class="section-title">📊 市场环境</div>
        <div class="market-context-grid">
          <div class="context-item">
            <span class="context-label">大盘趋势</span>
            <span class="context-value" :class="`trend--${dashboard.market_context.index_trend}`">
              {{ trendLabel(dashboard.market_context.index_trend) }}
            </span>
          </div>
          <div class="context-item">
            <span class="context-label">板块强弱</span>
            <span class="context-value">{{ strengthLabel(dashboard.market_context.sector_strength) }}</span>
          </div>
          <div class="context-item">
            <span class="context-label">市场情绪</span>
            <span class="context-value">{{ sentimentLabel(dashboard.market_context.market_sentiment) }}</span>
          </div>
        </div>
      </div>

      <!-- 辩论摘要 -->
      <div v-if="dashboard.debate_summary" class="dashboard-section">
        <div class="section-title">⚔️ 多空辩论</div>
        <div class="debate-grid">
          <div class="debate-side debate-bull">
            <span class="debate-label">🐂 多方</span>
            <span class="debate-text">{{ dashboard.debate_summary.bull_core_thesis }}</span>
          </div>
          <div class="debate-side debate-bear">
            <span class="debate-label">🐻 空方</span>
            <span class="debate-text">{{ dashboard.debate_summary.bear_core_thesis }}</span>
          </div>
        </div>
        <div v-if="dashboard.debate_summary.manager_verdict" class="debate-verdict">
          <span class="verdict-label">裁决:</span> {{ dashboard.debate_summary.manager_verdict }}
          <span v-if="dashboard.debate_summary.confidence_shift" class="confidence-shift">
            ({{ dashboard.debate_summary.confidence_shift }})
          </span>
        </div>
      </div>

      <!-- 风险评估 -->
      <div v-if="dashboard.risk_assessment" class="dashboard-section">
        <div class="section-title">🛡️ 风险评估</div>
        <div class="risk-views">
          <div v-if="dashboard.risk_assessment.aggressive_view" class="risk-view-item">
            <span class="risk-label">激进:</span> {{ dashboard.risk_assessment.aggressive_view }}
          </div>
          <div v-if="dashboard.risk_assessment.conservative_view" class="risk-view-item">
            <span class="risk-label">保守:</span> {{ dashboard.risk_assessment.conservative_view }}
          </div>
        </div>
        <div v-if="dashboard.risk_assessment.verdict" class="risk-verdict">
          {{ dashboard.risk_assessment.verdict }}
          <span v-if="dashboard.risk_assessment.max_acceptable_position" class="risk-position">
            | 建议仓位: {{ dashboard.risk_assessment.max_acceptable_position }}
          </span>
        </div>
      </div>

      <!-- 策略意见 -->
      <div v-if="dashboard.skill_opinions?.length" class="dashboard-section">
        <div class="section-title">🎯 策略评估</div>
        <div class="skill-opinions">
          <div v-for="(skill, idx) in dashboard.skill_opinions" :key="idx" class="skill-item">
            <span class="skill-name">{{ skill.skill_name }}</span>
            <span class="skill-signal" :class="`signal--${skill.signal}`">{{ signalLabel(skill.signal) }}</span>
            <span class="skill-obs">{{ skill.key_observation }}</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="dashboard-actions">
        <button class="action-btn" @click="$emit('annotate')" title="在K线图上标注信号">
          📍 在K线标注
        </button>
        <button class="action-btn" @click="$emit('chat')" title="在侧边栏继续追问">
          💬 继续对话
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DashboardData } from '../../service/chatService'

defineProps<{
  dashboard: DashboardData
}>()

defineEmits<{
  'annotate': []
  'chat': []
}>()

function signalLabel(signal: string) {
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有', alert: '警戒' }
  return map[signal] || signal
}

function trendLabel(trend?: string) {
  const map: Record<string, string> = { up: '↑ 上涨', sideways: '→ 震荡', down: '↓ 下跌' }
  return map[trend || ''] || trend || '-'
}

function strengthLabel(strength?: string) {
  const map: Record<string, string> = { strong: '强势', neutral: '中性', weak: '弱势' }
  return map[strength || ''] || strength || '-'
}

function sentimentLabel(sentiment?: string) {
  const map: Record<string, string> = { greedy: '贪婪', neutral: '中性', fearful: '恐惧' }
  return map[sentiment || ''] || sentiment || '-'
}
</script>

<style scoped>
.dashboard-result {
  background: #1a2634;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 12px;
}

.dashboard-result__header {
  padding: 10px 16px;
  border-bottom: 1px solid #2a3a4a;
}

.dashboard-title {
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
}

.dashboard-result__body {
  padding: 12px 16px;
}

.dashboard-signal-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.signal-badge {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
}

.signal-badge--buy { background: #1b4332; color: #52c41a; }
.signal-badge--sell { background: #3b1325; color: #ff4d4f; }
.signal-badge--hold { background: #2a2000; color: #faad14; }
.signal-badge--alert { background: #2a1b00; color: #ffa940; }

.confidence-bar {
  flex: 1;
  height: 20px;
  background: #252525;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #0e639c, #4fc1ff);
  border-radius: 10px;
  transition: width 0.5s ease;
}

.confidence-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  color: #fff;
  font-weight: 500;
}

.dashboard-summary {
  font-size: 13px;
  color: #bbb;
  line-height: 1.5;
  margin-bottom: 12px;
}

/* Section shared */
.dashboard-section {
  margin-bottom: 14px;
  padding: 10px 12px;
  background: #1e2e3e;
  border-radius: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #8bb8d4;
  margin-bottom: 8px;
}

/* Market Context */
.market-context-grid {
  display: flex;
  gap: 16px;
}

.context-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-label {
  font-size: 11px;
  color: #777;
}

.context-value {
  font-size: 12px;
  color: #ccc;
  font-weight: 500;
}

.trend--up { color: #52c41a; }
.trend--down { color: #ff4d4f; }
.trend--sideways { color: #faad14; }

/* Debate */
.debate-grid {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.debate-side {
  flex: 1;
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
}

.debate-bull {
  background: #1b3328;
  border-left: 3px solid #52c41a;
}

.debate-bear {
  background: #33161e;
  border-left: 3px solid #ff4d4f;
}

.debate-label {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
  color: #aaa;
}

.debate-text {
  color: #ccc;
  line-height: 1.4;
}

.debate-verdict {
  font-size: 12px;
  color: #b8d4e8;
  padding-top: 6px;
  border-top: 1px solid #2a3a4a;
}

.verdict-label {
  font-weight: 600;
  color: #8bb8d4;
}

.confidence-shift {
  color: #888;
  font-size: 11px;
}

/* Risk Assessment */
.risk-views {
  margin-bottom: 6px;
}

.risk-view-item {
  font-size: 12px;
  color: #bbb;
  margin-bottom: 4px;
}

.risk-label {
  font-weight: 500;
  color: #aaa;
}

.risk-verdict {
  font-size: 12px;
  color: #e8b86b;
  padding-top: 6px;
  border-top: 1px solid #2a3a4a;
}

.risk-position {
  color: #888;
}

/* Skill Opinions */
.skill-opinions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.skill-name {
  color: #8bb8d4;
  font-weight: 500;
  min-width: 80px;
}

.skill-signal {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.signal--buy { background: #1b4332; color: #52c41a; }
.signal--sell { background: #3b1325; color: #ff4d4f; }
.signal--hold { background: #2a2000; color: #faad14; }

.skill-obs {
  color: #999;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  background: #253d52;
  border: 1px solid #3a5f7a;
  border-radius: 6px;
  color: #b8d4e8;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.action-btn:hover {
  background: #2d4f6a;
  border-color: #4a7fa0;
}
</style>
