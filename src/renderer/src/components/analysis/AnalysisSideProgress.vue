<template>
  <div class="analysis-side-progress">
    <!-- Agent 实时进度 -->
    <div class="progress-section" v-if="stages.length > 0">
      <div class="section-header">
        <span class="section-icon">⚡</span>
        <span>分析进度</span>
      </div>
      <div class="stage-list">
        <div
          v-for="stage in stageItems"
          :key="stage.key"
          class="stage-row"
          :class="stage.status"
        >
          <span class="stage-icon">{{ stage.icon }}</span>
          <span class="stage-label">{{ stage.label }}</span>
          <span class="stage-time" v-if="stage.duration">{{ stage.duration.toFixed(1) }}s</span>
        </div>
      </div>
    </div>

    <!-- 辩论过程 -->
    <div class="progress-section" v-if="debate">
      <div class="section-header">
        <span class="section-icon">⚖️</span>
        <span>多空辩论</span>
        <span class="round-badge" v-if="debate.totalRounds">
          {{ debate.round }}/{{ debate.totalRounds }}
        </span>
      </div>
      <div class="debate-live">
        <div class="debate-row debate-bull" v-if="debate.bull">
          <span class="debate-tag">📈 多</span>
          <span class="debate-text">{{ truncate(debate.bull, 80) }}</span>
        </div>
        <div class="debate-row debate-bear" v-if="debate.bear">
          <span class="debate-tag">📉 空</span>
          <span class="debate-text">{{ truncate(debate.bear, 80) }}</span>
        </div>
      </div>
    </div>

    <!-- 风险讨论 -->
    <div class="progress-section" v-if="riskDebate">
      <div class="section-header">
        <span class="section-icon">🛡️</span>
        <span>风险评估</span>
      </div>
      <div class="risk-live">
        <div
          v-for="persp in (riskDebate.perspectives || [])"
          :key="persp"
          class="risk-row"
        >
          <span class="risk-tag">{{ perspIcon(persp) }}</span>
          <span class="risk-text">{{ truncate(riskDebate.content?.[persp] || '', 60) }}</span>
        </div>
      </div>
    </div>

    <!-- 思考状态 -->
    <div class="progress-section thinking-section" v-if="thinking && !stages.length">
      <div class="section-header">
        <span class="section-icon thinking-anim">🧠</span>
        <span>思考中...</span>
      </div>
      <div class="thinking-preview">{{ truncate(thinking, 120) }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StageInfo, DebateInfo, RiskDebateInfo } from '../../service/chatService'

const props = defineProps<{
  stages: StageInfo[]
  debate: DebateInfo | null
  riskDebate: RiskDebateInfo | null
  thinking: string
  mode: string
}>()

const stageDefinitions: Record<string, { key: string; label: string }[]> = {
  quick: [
    { key: 'technical', label: '技术分析' },
    { key: 'intel', label: '情报采集' },
    { key: 'decision', label: '综合决策' }
  ],
  deep: [
    { key: 'technical', label: '技术分析' },
    { key: 'intel', label: '情报采集' },
    { key: 'risk', label: '风险评估' },
    { key: 'debate', label: '多空辩论' },
    { key: 'risk_debate', label: '风险讨论' },
    { key: 'skill', label: '策略会诊' },
    { key: 'decision', label: '综合决策' }
  ]
}

const stageItems = computed(() => {
  const defs = stageDefinitions[props.mode] || stageDefinitions.quick
  return defs.map(def => {
    const s = props.stages.find(st => st.stage === def.key)
    let status = 'pending'
    let icon = '○'
    let duration: number | undefined

    if (s) {
      status = s.status
      duration = s.duration
      if (s.status === 'completed') icon = '✅'
      else if (s.status === 'running') icon = '🔄'
      else if (s.status === 'error') icon = '❌'
    }

    return { ...def, status, icon, duration }
  })
})

function perspIcon(persp: string) {
  if (persp.includes('aggressive') || persp.includes('激进')) return '🔥'
  if (persp.includes('conservative') || persp.includes('保守')) return '🛡️'
  return '⚖️'
}

function truncate(text: string, max: number) {
  return text.length > max ? text.slice(0, max) + '...' : text
}
</script>

<style scoped>
.analysis-side-progress {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
}

.progress-section {
  background: #1e2a36;
  border-radius: 8px;
  padding: 10px 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #b0c4d8;
  margin-bottom: 8px;
}

.section-icon {
  font-size: 14px;
}

.round-badge {
  margin-left: auto;
  font-size: 11px;
  background: #2a3f52;
  padding: 2px 6px;
  border-radius: 4px;
  color: #8bb8d4;
}

/* Stage list */
.stage-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stage-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 6px;
  border-radius: 4px;
}

.stage-row.running {
  background: #1a3050;
}

.stage-icon {
  width: 18px;
  text-align: center;
  font-size: 12px;
}

.stage-label {
  flex: 1;
  color: #ccc;
}

.stage-time {
  font-size: 11px;
  color: #888;
}

/* Debate live */
.debate-live, .risk-live {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.debate-row, .risk-row {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  font-size: 11px;
}

.debate-tag, .risk-tag {
  flex-shrink: 0;
  font-size: 12px;
}

.debate-text, .risk-text {
  color: #aaa;
  line-height: 1.4;
}

.debate-bull { border-left: 2px solid #52c41a; padding-left: 6px; }
.debate-bear { border-left: 2px solid #ff4d4f; padding-left: 6px; }

/* Thinking */
.thinking-section .thinking-preview {
  font-size: 11px;
  color: #888;
  line-height: 1.4;
}

.thinking-anim {
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
