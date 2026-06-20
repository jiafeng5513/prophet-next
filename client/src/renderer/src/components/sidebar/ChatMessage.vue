<template>
  <div class="chat-message" :class="[`chat-message--${message.role}`, { 'chat-message--streaming': isStreaming }]">
    <!-- 用户消息 -->
    <div v-if="message.role === 'user'" class="chat-message__user">
      <div class="chat-message__bubble chat-message__bubble--user">
        {{ message.content }}
      </div>
    </div>

    <!-- Assistant 消息 -->
    <div v-else class="chat-message__assistant">
      <!-- 思考过程 (折叠) -->
      <div v-if="message.metadata?.thinking" class="chat-message__thinking" @click="thinkingExpanded = !thinkingExpanded">
        <span class="thinking-toggle">{{ thinkingExpanded ? '▼' : '▶' }}</span>
        <span class="thinking-label">思考过程</span>
      </div>
      <div v-if="thinkingExpanded && message.metadata?.thinking" class="chat-message__thinking-content">
        {{ message.metadata.thinking }}
      </div>

      <!-- 工具调用 (简洁卡片) -->
      <div v-if="message.metadata?.tools?.length" class="chat-message__tools">
        <div v-for="tool in message.metadata.tools" :key="tool.name" class="tool-chip">
          <span class="tool-icon">{{ tool.status === 'done' ? '✓' : '⟳' }}</span>
          <span class="tool-name">{{ tool.name }}</span>
          <span v-if="tool.duration" class="tool-duration">{{ tool.duration.toFixed(1) }}s</span>
        </div>
      </div>

      <!-- 阶段进度 (简洁) -->
      <div v-if="message.metadata?.stages?.length" class="chat-message__stages">
        <span v-for="stage in message.metadata.stages" :key="stage.stage" class="stage-badge" :class="`stage-badge--${stage.status}`">
          {{ stageIcon(stage.status) }} {{ stage.stage }}
        </span>
      </div>

      <!-- 正文 -->
      <div class="chat-message__bubble chat-message__bubble--assistant" v-html="renderedContent"></div>

      <!-- Dashboard 摘要 -->
      <div v-if="message.metadata?.dashboard" class="chat-message__dashboard">
        <span v-if="message.metadata.dashboard.signal" class="dashboard-signal" :class="`signal-${message.metadata.dashboard.signal}`">
          {{ signalLabel(message.metadata.dashboard.signal) }}
        </span>
        <span v-if="message.metadata.dashboard.confidence != null" class="dashboard-confidence">
          置信度: {{ (message.metadata.dashboard.confidence * 100).toFixed(0) }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { ChatMessage } from '../../service/chatService'

const props = defineProps<{
  message: ChatMessage
  isStreaming?: boolean
}>()

const thinkingExpanded = ref(false)

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return md.render(props.message.content)
})

function stageIcon(status: string) {
  switch (status) {
    case 'completed': return '✅'
    case 'running': return '🔄'
    case 'error': return '❌'
    default: return '○'
  }
}

function signalLabel(signal: string) {
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有', alert: '警戒' }
  return map[signal] || signal
}
</script>

<style scoped>
.chat-message {
  padding: 6px 12px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-message__user {
  display: flex;
  justify-content: flex-end;
}

.chat-message__bubble {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.chat-message__bubble--user {
  background: #0e639c;
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.chat-message__bubble--assistant {
  background: #2d2d2d;
  color: #e0e0e0;
  border-bottom-left-radius: 4px;
}

.chat-message__bubble--assistant :deep(p) {
  margin: 0 0 8px;
}

.chat-message__bubble--assistant :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-message__bubble--assistant :deep(pre) {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 8px;
  overflow-x: auto;
  font-size: 12px;
}

.chat-message__bubble--assistant :deep(code) {
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
}

.chat-message__bubble--assistant :deep(a) {
  color: #4fc1ff;
}

.chat-message__thinking {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 11px;
  color: #888;
  user-select: none;
}

.chat-message__thinking:hover {
  color: #bbb;
}

.thinking-label {
  font-style: italic;
}

.chat-message__thinking-content {
  padding: 6px 12px;
  font-size: 11px;
  color: #999;
  background: #1a1a1a;
  border-radius: 6px;
  margin: 2px 0 6px;
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.chat-message__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.tool-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  background: #1e3a5f;
  border-radius: 10px;
  font-size: 11px;
  color: #7ec8e3;
}

.tool-duration {
  color: #888;
  font-size: 10px;
}

.chat-message__stages {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.stage-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #252525;
  color: #aaa;
}

.stage-badge--completed { color: #4ec9b0; }
.stage-badge--running { color: #dcdcaa; }
.stage-badge--error { color: #f48771; }

.chat-message__dashboard {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding: 6px 10px;
  background: #1a2634;
  border-radius: 8px;
  font-size: 12px;
}

.dashboard-signal {
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.signal-buy { background: #1b4332; color: #52c41a; }
.signal-sell { background: #3b1325; color: #ff4d4f; }
.signal-hold { background: #2a2000; color: #faad14; }
.signal-alert { background: #2a1b00; color: #ffa940; }

.dashboard-confidence {
  color: #aaa;
}

.chat-message--streaming .chat-message__bubble--assistant::after {
  content: '▎';
  animation: blink 0.8s infinite;
  color: #4fc1ff;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
