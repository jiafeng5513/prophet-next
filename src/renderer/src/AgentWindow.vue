<template>
  <div class="agent-window">
    <!-- 顶部工具栏 -->
    <div class="agent-window__toolbar">
      <div class="toolbar-left">
        <span class="window-title">💬 AI 助手</span>
        <div class="mode-select">
          <select v-model="currentMode" @change="setMode(currentMode)">
            <option v-for="mode in allowedModes" :key="mode" :value="mode">
              {{ modeLabels[mode] }}
            </option>
          </select>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" title="历史会话" @click="showSessions = !showSessions">☰</button>
        <button class="toolbar-btn" @click="newChat" title="新对话">🗑️</button>
        <span class="status-dot" :class="connected ? 'connected' : 'disconnected'"></span>
      </div>
    </div>

    <!-- 会话列表 -->
    <SessionList
      v-if="showSessions"
      :sessions="sessions"
      :current-session-id="currentSessionId"
      @close="showSessions = false"
      @switch="onSwitchSession"
      @delete="onDeleteSession"
    />

    <!-- 主内容区 -->
    <div class="agent-window__body" ref="bodyRef" v-show="!showSessions">
      <!-- Agent 进度 (quick/deep 模式) -->
      <AgentProgress
        v-if="showProgress"
        :stages="streamResult.stages"
        :mode="currentMode"
      />

      <!-- 消息列表 -->
      <div class="agent-window__messages">
        <template v-for="msg in messages" :key="msg.id">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="aw-msg aw-msg--user">
            <div class="aw-msg__bubble aw-msg__bubble--user">{{ msg.content }}</div>
          </div>

          <!-- Assistant 消息 -->
          <div v-else class="aw-msg aw-msg--assistant">
            <!-- 思考 -->
            <ThinkingBlock v-if="msg.metadata?.thinking" :content="msg.metadata.thinking" />

            <!-- 工具调用 -->
            <ToolCallCard v-for="tool in (msg.metadata?.tools || [])" :key="tool.name" :tool="tool" />

            <!-- 辩论面板 -->
            <DebatePanel v-if="msg.metadata?.debate" :debate="msg.metadata.debate" />

            <!-- 风险讨论 -->
            <RiskDebatePanel v-if="msg.metadata?.riskDebate" :risk-debate="msg.metadata.riskDebate" />

            <!-- 正文（dashboard 已有时不重复渲染 JSON） -->
            <StreamRenderer v-if="!msg.metadata?.dashboard" :content="msg.content" />

            <!-- 结果 Dashboard -->
            <DashboardResult
              v-if="msg.metadata?.dashboard"
              :dashboard="msg.metadata.dashboard"
              @annotate="onAnnotate(msg)"
              @chat="onContinueChat"
            />
            <!-- 雷达图 & 导出 -->
            <div v-if="msg.metadata?.dashboard" class="aw-dashboard-extras">
              <AnalysisRadar
                v-if="getRadarDimensions(msg.metadata.dashboard).length >= 3"
                :dimensions="getRadarDimensions(msg.metadata.dashboard)"
              />
              <AnalysisExport
                :dashboard="msg.metadata.dashboard"
                :stock-code="symbolInput"
                :stock-name="''"
              />
            </div>
          </div>
        </template>

        <!-- 流式 (正在生成) -->
        <div v-if="isStreaming" class="aw-msg aw-msg--assistant aw-msg--streaming">
          <ThinkingBlock v-if="streamResult.thinking" :content="streamResult.thinking" />
          <ToolCallCard v-for="tool in streamResult.tools" :key="tool.name" :tool="tool" />
          <DebatePanel v-if="streamResult.debate" :debate="streamResult.debate" />
          <RiskDebatePanel v-if="streamResult.riskDebate" :risk-debate="streamResult.riskDebate" />
          <StreamRenderer :content="streamResult.content" :streaming="true" />
        </div>

        <!-- Plan 模式: 等待用户确认 -->
        <PlanCard
          v-if="pendingPlan"
          :plan="pendingPlan"
          :executing="planExecuting"
          @execute="onPlanExecute"
          @modify="onPlanModify"
          @cancel="onPlanCancel"
        />

        <!-- 多股票对比分析 -->
        <CompareAnalysis
          v-if="compareItems.length > 1"
          :items="compareItems"
          @close="compareItems = []"
        />
      </div>
    </div>

    <!-- 输入区 -->
    <div class="agent-window__input">
      <ChatInput
        ref="inputRef"
        :current-mode="currentMode"
        :allowed-modes="allowedModes"
        :skills="skills"
        :selected-skills="selectedSkills"
        :is-streaming="isStreaming"
        @send="onSend"
        @stop="stopStreaming"
        @mode-change="setMode"
        @skill-toggle="onSkillToggle"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import AgentProgress from './components/agent/AgentProgress.vue'
import DebatePanel from './components/agent/DebatePanel.vue'
import RiskDebatePanel from './components/agent/RiskDebatePanel.vue'
import ThinkingBlock from './components/agent/ThinkingBlock.vue'
import ToolCallCard from './components/agent/ToolCallCard.vue'
import StreamRenderer from './components/agent/StreamRenderer.vue'
import DashboardResult from './components/agent/DashboardResult.vue'
import PlanCard from './components/agent/PlanCard.vue'
import ChatInput from './components/sidebar/ChatInput.vue'
import SessionList from './components/sidebar/SessionList.vue'
import AnalysisRadar from './components/analysis/AnalysisRadar.vue'
import AnalysisExport from './components/analysis/AnalysisExport.vue'
import CompareAnalysis from './components/analysis/CompareAnalysis.vue'
import { useChat } from './composables/useChat'
import type { ChatMode, ChatMessage } from './service/chatService'
import { annotateFromDashboard } from './service/annotationService'

const modeLabels: Record<ChatMode, string> = {
  chat: '💬 对话',
  quick: '⚡ 快速',
  deep: '🔬 深度',
  plan: '📋 计划'
}

// 浮动助手: 支持对话和快速分析
const allowedModes: ChatMode[] = ['chat', 'quick', 'deep']

const {
  messages,
  sessions,
  currentSessionId,
  currentMode,
  skills,
  selectedSkills,
  connected,
  isStreaming,
  streamResult,
  init,
  sendMessage,
  stopStreaming,
  setMode,
  newChat,
  switchSession,
  removeSession
} = useChat({
  defaultMode: 'chat',
  allowedModes,
  showUpgradeHint: false
})

const bodyRef = ref<HTMLElement | null>(null)
const inputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const symbolInput = ref('')
const showSessions = ref(false)
const compareItems = ref<Array<{ code: string; dashboard: Record<string, unknown> }>>([])

// Plan 模式状态
const pendingPlan = ref<{ steps: { description: string; done?: boolean; running?: boolean }[]; estimated_time?: string; estimated_tokens?: number } | null>(null)
const planExecuting = ref(false)

// 显示进度条的模式
const showProgress = computed(() =>
  ['quick', 'deep', 'plan'].includes(currentMode.value) &&
  (isStreaming.value || streamResult.value.stages.length > 0)
)

// 从 URL 参数获取初始值
onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  const symbol = params.get('symbol')
  const mode = params.get('mode') as ChatMode | null
  const sessionId = params.get('sessionId')

  if (symbol) symbolInput.value = symbol
  if (mode && allowedModes.includes(mode)) setMode(mode)

  init()

  // 如果带了 symbol 参数，自动开始分析
  if (symbol) {
    nextTick(() => {
      sendMessage(`分析 ${symbol}`, { symbol, mode: currentMode.value })
    })
  }
})

// 自动滚动 — 监听所有可能导致内容变化的数据源
const _scrollTrigger = computed(() => [
  messages.value.length,
  streamResult.value.content,
  streamResult.value.thinking,
  streamResult.value.stages.length,
  streamResult.value.tools.length,
])
watch(_scrollTrigger, () => {
  nextTick(() => {
    if (bodyRef.value) {
      bodyRef.value.scrollTop = bodyRef.value.scrollHeight
    }
  })
})

function onSend(text: string) {
  sendMessage(text, { symbol: symbolInput.value || undefined })
}

function onSymbolEnter() {
  if (symbolInput.value.trim()) {
    sendMessage(`分析 ${symbolInput.value}`, { symbol: symbolInput.value, mode: currentMode.value })
  }
}

function onSkillToggle(skillId: string) {
  if (selectedSkills.value.includes(skillId)) {
    selectedSkills.value = []
  } else {
    selectedSkills.value = [skillId]
  }
}

function onAnnotate(msg: ChatMessage) {
  const dashboard = msg.metadata?.dashboard
  if (dashboard) {
    annotateFromDashboard(symbolInput.value, dashboard, 'current')
  }
}

function onContinueChat() {
  // IPC: 通知侧边栏聚焦
  if (window.electronAPI?.invoke) {
    window.electronAPI.invoke('agent:sync-result', {
      sessionId: messages.value.length > 0 ? 'current' : null,
      summary: streamResult.value.content?.slice(0, 200)
    })
  }
}

// Plan 模式: 监听 plan_ready 事件 (dashboard.plan)
watch(() => streamResult.value.dashboard, (dashboard) => {
  if (dashboard && (dashboard as Record<string, unknown>).plan) {
    pendingPlan.value = (dashboard as Record<string, unknown>).plan as typeof pendingPlan.value
  }
})

function onPlanExecute() {
  if (!pendingPlan.value) return
  planExecuting.value = true
  pendingPlan.value = null
  // 发送确认执行，使用 full 模式
  sendMessage('确认执行分析计划', { symbol: symbolInput.value || undefined, mode: 'full' })
  planExecuting.value = false
}

function onPlanModify() {
  // 保留计划在界面上，用户可在输入框修改后重新提交
  pendingPlan.value = null
}

function onPlanCancel() {
  pendingPlan.value = null
  stopStreaming()
}

// ==================== 会话管理 ====================
function onSwitchSession(sessionId: string) {
  switchSession(sessionId)
  showSessions.value = false
}

function onDeleteSession(sessionId: string) {
  removeSession(sessionId)
}

// ==================== 雷达图维度提取 ====================
function getRadarDimensions(dashboard: Record<string, unknown>) {
  const dims: { key: string; label: string; value: number }[] = []
  const d = dashboard as Record<string, any>
  if (d.confidence != null) dims.push({ key: 'confidence', label: '置信度', value: Math.round(d.confidence * 100) })
  if (d.market_context) {
    const mc = d.market_context
    if (mc.strength) {
      const strengthMap: Record<string, number> = { strong: 80, moderate: 55, weak: 30 }
      dims.push({ key: 'strength', label: '趋势', value: strengthMap[mc.strength] || 50 })
    }
    if (mc.sentiment) {
      const sentMap: Record<string, number> = { bullish: 80, neutral: 50, bearish: 25 }
      dims.push({ key: 'sentiment', label: '情绪', value: sentMap[mc.sentiment] || 50 })
    }
  }
  if (d.risk_assessment?.max_acceptable_position) {
    const pos = parseInt(d.risk_assessment.max_acceptable_position)
    if (!isNaN(pos)) dims.push({ key: 'position', label: '仓位', value: pos })
  }
  if (d.debate_summary?.confidence_shift != null) {
    dims.push({ key: 'debate', label: '辩论', value: Math.min(100, Math.max(0, 50 + d.debate_summary.confidence_shift * 50)) })
  }
  if (d.skill_opinions?.length) {
    const buyCount = d.skill_opinions.filter((s: any) => ['buy', '买入'].includes(s.signal)).length
    dims.push({ key: 'skills', label: '策略', value: Math.round((buyCount / d.skill_opinions.length) * 100) })
  }
  return dims
}

// ==================== 对比分析收集 ====================
watch(
  () => streamResult.value.dashboard,
  (dashboard) => {
    if (dashboard && symbolInput.value) {
      const existing = compareItems.value.find(i => i.code === symbolInput.value)
      if (!existing) {
        compareItems.value.push({ code: symbolInput.value, dashboard: dashboard as Record<string, unknown> })
      }
    }
  }
)
</script>

<style scoped>
.agent-window {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1e1e1e;
  color: #e0e0e0;
}

.agent-window__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #252525;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.window-title {
  font-size: 13px;
  font-weight: 600;
  color: #e0e0e0;
}

.mode-select {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #aaa;
}

.mode-select select {
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 4px;
  color: #e0e0e0;
  padding: 4px 8px;
  font-size: 12px;
}

.toolbar-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
}

.toolbar-btn:hover {
  color: #ccc;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected { background: #4ec9b0; }
.status-dot.disconnected { background: #666; }

.agent-window__body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  scrollbar-width: thin;
  scrollbar-color: #444 transparent;
}

.agent-window__messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.aw-msg--user {
  display: flex;
  justify-content: flex-end;
}

.aw-msg__bubble--user {
  background: #0e639c;
  color: #fff;
  padding: 8px 14px;
  border-radius: 12px 12px 4px 12px;
  max-width: 70%;
  font-size: 13px;
  line-height: 1.5;
}

.aw-msg--assistant {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.aw-msg--streaming {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0.5; }
  to { opacity: 1; }
}

.agent-window__input {
  flex-shrink: 0;
}

.aw-dashboard-extras {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-top: 8px;
  flex-wrap: wrap;
}
</style>
