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
      <div v-if="dashboard.summary || dashboard.analysis_summary" class="dashboard-summary">
        {{ dashboard.summary || dashboard.analysis_summary }}
      </div>

      <!-- 评分仪表 -->
      <div v-if="dashboard.sentiment_score != null" class="dashboard-section">
        <div class="section-title">📈 综合评分</div>
        <div class="score-gauge">
          <div class="score-bar">
            <div class="score-fill" :style="{ width: Math.min(100, Math.max(0, dashboard.sentiment_score)) + '%' }" :class="scoreClass"></div>
          </div>
          <span class="score-number" :class="scoreClass">{{ dashboard.sentiment_score }}</span>
          <span class="score-label">{{ scoreLabel }}</span>
        </div>
      </div>

      <!-- 关键要点 (checklist) -->
      <div v-if="keyPoints.length" class="dashboard-section">
        <div class="section-title">✅ 关键要点</div>
        <ul class="key-points-list">
          <li v-for="(point, idx) in keyPoints" :key="idx" class="key-point-item">
            {{ point }}
          </li>
        </ul>
      </div>

      <!-- 操作建议 (含价格水平) -->
      <div v-if="dashboard.operation_advice" class="dashboard-section">
        <div class="section-title">🎯 操作建议</div>
        <div class="operation-advice">
          <template v-if="typeof dashboard.operation_advice === 'string'">
            <p class="advice-text">{{ dashboard.operation_advice }}</p>
          </template>
          <template v-else-if="typeof dashboard.operation_advice === 'object'">
            <div v-if="dashboard.operation_advice.no_position" class="advice-block">
              <span class="advice-label">空仓者:</span>
              <span class="advice-content">{{ dashboard.operation_advice.no_position }}</span>
            </div>
            <div v-if="dashboard.operation_advice.has_position" class="advice-block">
              <span class="advice-label">持仓者:</span>
              <span class="advice-content">{{ dashboard.operation_advice.has_position }}</span>
            </div>
            <div v-if="dashboard.operation_advice.entry_price" class="price-level">
              入场参考: <strong>{{ dashboard.operation_advice.entry_price }}</strong>
            </div>
            <div v-if="dashboard.operation_advice.stop_loss" class="price-level price-level--loss">
              止损位: <strong>{{ dashboard.operation_advice.stop_loss }}</strong>
            </div>
            <div v-if="dashboard.operation_advice.take_profit" class="price-level price-level--profit">
              止盈位: <strong>{{ dashboard.operation_advice.take_profit }}</strong>
            </div>
          </template>
        </div>
      </div>

      <!-- 详细指标数值表 -->
      <div v-if="dashboard.dashboard && typeof dashboard.dashboard === 'object'" class="dashboard-section">
        <div class="section-title">📋 指标数据</div>
        <table class="indicators-table">
          <tbody>
            <tr v-for="(value, key) in flatIndicators" :key="key">
              <td class="indicator-key">{{ key }}</td>
              <td class="indicator-value">{{ value }}</td>
            </tr>
          </tbody>
        </table>
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
        <table class="strategy-compare-table">
          <thead>
            <tr>
              <th>策略</th>
              <th>信号</th>
              <th>置信度</th>
              <th>核心观察</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(skill, idx) in dashboard.skill_opinions" :key="idx">
              <td class="skill-name-cell">{{ skill.skill_name }}</td>
              <td><span class="skill-signal" :class="`signal--${skill.signal}`">{{ signalLabel(skill.signal) }}</span></td>
              <td>{{ skill.confidence != null ? (skill.confidence * 100).toFixed(0) + '%' : '-' }}</td>
              <td class="skill-obs-cell">{{ skill.key_observation }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 风险警告 -->
      <div v-if="dashboard.risk_warning" class="dashboard-section risk-warning-section">
        <div class="section-title">⚠️ 风险警告</div>
        <div class="risk-warning-text">{{ dashboard.risk_warning }}</div>
      </div>

      <!-- 相关新闻 -->
      <div v-if="newsItems.length" class="dashboard-section">
        <div class="section-title">📰 相关新闻</div>
        <ul class="news-list">
          <li v-for="(item, idx) in newsItems" :key="idx" class="news-item">
            <span class="news-impact" :class="`news-impact--${item.impact}`">●</span>
            <a v-if="item.url" :href="item.url" target="_blank" rel="noopener" class="news-link">{{ item.title }}</a>
            <span v-else class="news-title-text">{{ item.title }}</span>
          </li>
        </ul>
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
import { computed } from 'vue'
import type { DashboardData } from '../../service/chatService'

const props = defineProps<{
  dashboard: DashboardData
}>()

defineEmits<{
  'annotate': []
  'chat': []
}>()

// 关键要点列表
const keyPoints = computed(() => {
  const kp = (props.dashboard as any).key_points
  if (!kp) return []
  if (Array.isArray(kp)) return kp
  if (typeof kp === 'string') return kp.split('\n').filter((s: string) => s.trim())
  return []
})

// 评分等级
const scoreClass = computed(() => {
  const score = (props.dashboard as any).sentiment_score
  if (score == null) return ''
  if (score >= 70) return 'score--high'
  if (score >= 40) return 'score--mid'
  return 'score--low'
})

const scoreLabel = computed(() => {
  const score = (props.dashboard as any).sentiment_score
  if (score == null) return ''
  if (score >= 80) return '强烈看多'
  if (score >= 60) return '看多'
  if (score >= 40) return '中性'
  if (score >= 20) return '看空'
  return '强烈看空'
})

// 扁平化指标数据
const flatIndicators = computed(() => {
  const d = (props.dashboard as any).dashboard
  if (!d || typeof d !== 'object') return {}
  const result: Record<string, string> = {}
  for (const [key, val] of Object.entries(d)) {
    if (val != null && typeof val !== 'object') {
      result[key] = String(val)
    }
  }
  return result
})

// 新闻列表 — 从 intelligence.key_news 或顶层 key_news 中提取
const newsItems = computed(() => {
  const d = props.dashboard as any
  const raw = d?.intelligence?.key_news || d?.key_news
  if (!Array.isArray(raw)) return []
  return raw
    .filter((item: any) => item && item.title)
    .slice(0, 8)
    .map((item: any) => ({
      title: item.title,
      impact: item.impact || 'neutral',
      url: item.url || '',
    }))
})

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

/* ===== 评分仪表 ===== */
.score-gauge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-bar {
  flex: 1;
  height: 8px;
  background: #252525;
  border-radius: 4px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.score-fill.score--high { background: #52c41a; }
.score-fill.score--mid { background: #faad14; }
.score-fill.score--low { background: #ff4d4f; }

.score-number {
  font-size: 18px;
  font-weight: 700;
  min-width: 32px;
}

.score-number.score--high { color: #52c41a; }
.score-number.score--mid { color: #faad14; }
.score-number.score--low { color: #ff4d4f; }

.score-label {
  font-size: 12px;
  color: #888;
}

/* ===== 关键要点 ===== */
.key-points-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.key-point-item {
  padding: 4px 0;
  font-size: 13px;
  color: #d0d0d0;
  line-height: 1.5;
}

.key-point-item::before {
  content: '✓ ';
  color: #52c41a;
}

/* ===== 操作建议 ===== */
.operation-advice {
  font-size: 13px;
  color: #d0d0d0;
}

.advice-text {
  margin: 0;
  line-height: 1.6;
}

.advice-block {
  margin-bottom: 6px;
}

.advice-label {
  color: #7ec8e3;
  font-weight: 500;
  margin-right: 6px;
}

.advice-content {
  color: #d0d0d0;
}

.price-level {
  margin-top: 4px;
  font-size: 12px;
  color: #aaa;
}

.price-level strong {
  color: #7ec8e3;
}

.price-level--loss strong { color: #ff4d4f; }
.price-level--profit strong { color: #52c41a; }

/* ===== 指标数据表 ===== */
.indicators-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.indicators-table td {
  padding: 4px 8px;
  border-bottom: 1px solid #2a3a4a;
}

.indicator-key {
  color: #888;
  width: 40%;
}

.indicator-value {
  color: #d0d0d0;
}

/* ===== 策略对比表 ===== */
.strategy-compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.strategy-compare-table th {
  text-align: left;
  padding: 6px 8px;
  color: #888;
  border-bottom: 1px solid #2a3a4a;
  font-weight: 500;
}

.strategy-compare-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #1f2f3f;
  color: #d0d0d0;
}

.skill-name-cell {
  font-weight: 500;
  color: #7ec8e3;
}

.skill-obs-cell {
  color: #aaa;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 风险警告 ===== */
.risk-warning-section {
  border: 1px solid #5a3000;
  border-radius: 6px;
  background: rgba(250, 173, 20, 0.05);
}

.risk-warning-text {
  font-size: 13px;
  color: #faad14;
  line-height: 1.6;
}

/* ===== 相关新闻 ===== */
.news-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.news-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px 0;
  font-size: 12px;
  line-height: 1.5;
}

.news-impact {
  font-size: 8px;
  margin-top: 4px;
  flex-shrink: 0;
}

.news-impact--positive { color: #52c41a; }
.news-impact--negative { color: #ff4d4f; }
.news-impact--neutral { color: #8c8c8c; }

.news-link {
  color: #69b1ff;
  text-decoration: none;
  word-break: break-all;
}

.news-link:hover {
  text-decoration: underline;
  color: #91caff;
}

.news-title-text {
  color: #b8d4e8;
}
</style>
