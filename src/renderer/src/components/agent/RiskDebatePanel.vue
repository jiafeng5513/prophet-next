<template>
  <div class="risk-debate-panel">
    <div class="risk-debate-panel__header">
      <span class="risk-title">风险三方讨论</span>
      <span class="risk-status" :class="`status-${riskDebate.status}`">
        {{ riskDebate.status === 'running' ? '进行中' : '已完成' }}
      </span>
    </div>

    <div class="risk-debate-panel__content">
      <div
        v-for="perspective in riskDebate.perspectives"
        :key="perspective"
        class="risk-perspective"
        :class="`risk-perspective--${perspective}`"
      >
        <div class="risk-perspective__header">
          <span class="risk-perspective__icon">{{ perspectiveIcon(perspective) }}</span>
          <span class="risk-perspective__label">{{ perspectiveLabel(perspective) }}</span>
        </div>
        <div v-if="riskDebate.content[perspective]" class="risk-perspective__body" v-html="renderMd(riskDebate.content[perspective])"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import type { RiskDebateInfo } from '../../service/chatService'

defineProps<{
  riskDebate: RiskDebateInfo
}>()

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

function renderMd(text: string) {
  return md.render(text)
}

function perspectiveIcon(p: string) {
  switch (p) {
    case 'aggressive': return '🔥'
    case 'conservative': return '🛡️'
    case 'neutral': return '⚖️'
    default: return '💡'
  }
}

function perspectiveLabel(p: string) {
  switch (p) {
    case 'aggressive': return '激进派'
    case 'conservative': return '保守派'
    case 'neutral': return '中立派'
    default: return p
  }
}
</script>

<style scoped>
.risk-debate-panel {
  border-radius: 10px;
  background: #1a2634;
  margin-bottom: 12px;
  overflow: hidden;
}

.risk-debate-panel__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #2a3a4a;
}

.risk-title {
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
  flex: 1;
}

.risk-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.status-running { background: #1a3a5c; color: #7ec8e3; }
.status-completed { background: #1b3a2a; color: #4ec9b0; }

.risk-debate-panel__content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.risk-perspective {
  border-radius: 8px;
  overflow: hidden;
  padding: 8px 12px;
}

.risk-perspective--aggressive { background: #2a1500; border-left: 3px solid #f59e0b; }
.risk-perspective--conservative { background: #0f1a2e; border-left: 3px solid #3b82f6; }
.risk-perspective--neutral { background: #1a1a2a; border-left: 3px solid #8b5cf6; }

.risk-perspective__header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 500;
}

.risk-perspective--aggressive .risk-perspective__label { color: #fbbf24; }
.risk-perspective--conservative .risk-perspective__label { color: #60a5fa; }
.risk-perspective--neutral .risk-perspective__label { color: #a78bfa; }

.risk-perspective__body {
  font-size: 12px;
  line-height: 1.5;
  color: #ccc;
}

.risk-perspective__body :deep(p) {
  margin: 0 0 4px;
}
</style>
