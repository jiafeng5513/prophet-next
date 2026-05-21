<template>
  <div class="agent-window">
    <!-- 顶部工具栏 -->
    <div class="agent-window__toolbar">
      <div class="toolbar-left">
        <div class="mode-select">
          <label>模式:</label>
          <select v-model="currentMode" @change="setMode(currentMode)">
            <option v-for="mode in allowedModes" :key="mode" :value="mode">
              {{ modeLabels[mode] }}
            </option>
          </select>
        </div>
        <div class="symbol-input">
          <label>标的:</label>
          <input v-model="symbolInput" placeholder="600519" @keydown.enter="onSymbolEnter" />
        </div>
      </div>
      <div class="toolbar-right">
        <span class="status-dot" :class="connected ? 'connected' : 'disconnected'"></span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="agent-window__body" ref="bodyRef">
      <!-- Agent 进度 (standard/full/specialist 模式) -->
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

            <!-- 正文 -->
            <StreamRenderer :content="msg.content" />

            <!-- 结果 Dashboard -->
            <DashboardResult
              v-if="msg.metadata?.dashboard"
              :dashboard="msg.metadata.dashboard"
              @annotate="onAnnotate(msg)"
              @chat="onContinueChat"
            />
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
import { useChat } from './composables/useChat'
import type { ChatMode, ChatMessage } from './service/chatService'

const modeLabels: Record<ChatMode, string> = {
  chat: '自由对话',
  quick: '快速分析',
  standard: '标准分析',
  full: '完整分析',
  specialist: '专家分析',
  plan: '计划模式'
}

// Agent Window 支持全部模式
const allowedModes: ChatMode[] = ['chat', 'quick', 'standard', 'full', 'specialist', 'plan']

const {
  messages,
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
  newChat
} = useChat({
  defaultMode: 'full',
  allowedModes,
  showUpgradeHint: false
})

const bodyRef = ref<HTMLElement | null>(null)
const inputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const symbolInput = ref('')

// Plan 模式状态
const pendingPlan = ref<{ steps: { description: string; done?: boolean; running?: boolean }[]; estimated_time?: string; estimated_tokens?: number } | null>(null)
const planExecuting = ref(false)

// 显示进度条的模式
const showProgress = computed(() =>
  ['standard', 'full', 'specialist', 'plan'].includes(currentMode.value) &&
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

// 自动滚动
watch([() => messages.value.length, () => streamResult.value.content], () => {
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
  // IPC: 通知主进程标注到 K 线图
  if (window.electronAPI?.invoke) {
    window.electronAPI.invoke('chart:add-annotations', {
      symbol: symbolInput.value,
      annotations: [{
        symbol: symbolInput.value,
        timestamp: Date.now(),
        type: msg.metadata?.dashboard?.signal || 'alert',
        label: `${msg.metadata?.dashboard?.signal || ''} (${((msg.metadata?.dashboard?.confidence || 0) * 100).toFixed(0)}%)`,
        price: 0,
        source: 'agent'
      }]
    })
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
  gap: 16px;
}

.mode-select,
.symbol-input {
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

.symbol-input input {
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 4px;
  color: #e0e0e0;
  padding: 4px 8px;
  font-size: 12px;
  width: 100px;
}

.symbol-input input:focus {
  border-color: #0e639c;
  outline: none;
}

.toolbar-right {
  display: flex;
  align-items: center;
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
</style>
