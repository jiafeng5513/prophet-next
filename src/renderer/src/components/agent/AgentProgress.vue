<template>
  <div class="agent-progress">
    <div class="agent-progress__title">分析进度</div>
    <div class="agent-progress__stages">
      <div
        v-for="stage in allStages"
        :key="stage.id"
        class="progress-stage"
        :class="`progress-stage--${stage.status}`"
      >
        <span class="progress-stage__icon">{{ stageIcon(stage.status) }}</span>
        <span class="progress-stage__name">{{ stage.label }}</span>
        <span v-if="stage.duration" class="progress-stage__duration">{{ stage.duration.toFixed(1) }}s</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StageInfo } from '../../service/chatService'

const props = defineProps<{
  stages: StageInfo[]
  mode: string
}>()

interface DisplayStage {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'error'
  duration?: number
}

// 根据模式决定所有预期阶段
const stageDefinitions: Record<string, { id: string; label: string }[]> = {
  standard: [
    { id: 'technical', label: 'Technical' },
    { id: 'intel', label: 'Intel' },
    { id: 'decision', label: 'Decision' }
  ],
  full: [
    { id: 'technical', label: 'Technical' },
    { id: 'intel', label: 'Intel' },
    { id: 'debate', label: 'Debate' },
    { id: 'risk', label: 'Risk' },
    { id: 'decision', label: 'Decision' }
  ],
  specialist: [
    { id: 'technical', label: 'Technical' },
    { id: 'intel', label: 'Intel' },
    { id: 'specialist', label: 'Specialist' },
    { id: 'debate', label: 'Debate' },
    { id: 'risk', label: 'Risk' },
    { id: 'decision', label: 'Decision' }
  ]
}

const allStages = computed<DisplayStage[]>(() => {
  const defs = stageDefinitions[props.mode] || stageDefinitions.standard
  return defs.map(def => {
    const actual = props.stages.find(s => s.stage === def.id)
    return {
      id: def.id,
      label: def.label,
      status: actual?.status || 'pending',
      duration: actual?.duration
    }
  })
})

function stageIcon(status: string) {
  switch (status) {
    case 'completed': return '✅'
    case 'running': return '🔄'
    case 'error': return '❌'
    default: return '○'
  }
}
</script>

<style scoped>
.agent-progress {
  padding: 12px 16px;
  background: #1a2634;
  border-radius: 10px;
  margin-bottom: 12px;
}

.agent-progress__title {
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.agent-progress__stages {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.progress-stage {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 12px;
  background: #252525;
  color: #888;
  transition: background 0.2s, color 0.2s;
}

.progress-stage--running {
  background: #1a3a5c;
  color: #7ec8e3;
  animation: pulse 1.5s infinite;
}

.progress-stage--completed {
  background: #1b3a2a;
  color: #4ec9b0;
}

.progress-stage--error {
  background: #3b1325;
  color: #f48771;
}

.progress-stage__icon {
  font-size: 12px;
}

.progress-stage__name {
  font-weight: 500;
}

.progress-stage__duration {
  font-size: 10px;
  color: #666;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
