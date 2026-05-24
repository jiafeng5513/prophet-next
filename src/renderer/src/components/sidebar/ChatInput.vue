<template>
  <div class="chat-input-area">
    <!-- 模式选择 -->
    <div class="chat-input-toolbar">
      <div class="mode-selector">
        <button
          v-for="mode in availableModes"
          :key="mode.id"
          class="mode-btn"
          :class="{ active: currentMode === mode.id }"
          :title="mode.desc"
          @click="$emit('mode-change', mode.id)"
        >
          {{ mode.label }}
        </button>
      </div>
      <div v-if="skills.length" class="skill-selector" @click="showSkillDropdown = !showSkillDropdown">
        <span class="skill-label">{{ selectedSkillName || '技能' }}</span>
        <span class="skill-arrow">▾</span>
        <!-- 技能下拉 -->
        <div v-if="showSkillDropdown" class="skill-dropdown">
          <div
            v-for="skill in skills"
            :key="skill.id"
            class="skill-option"
            :class="{ selected: selectedSkills.includes(skill.id) }"
            @click.stop="$emit('skill-toggle', skill.id)"
          >
            <span class="skill-option-name">{{ skill.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="chat-input-wrapper">
      <textarea
        ref="inputRef"
        v-model="inputText"
        class="chat-input"
        rows="1"
        :placeholder="placeholder"
        @keydown="handleKeydown"
        @input="autoResize"
      ></textarea>
      <button
        v-if="isStreaming"
        class="chat-stop-btn"
        title="停止生成"
        @click="$emit('stop')"
      >
        ■
      </button>
      <button
        v-else
        class="chat-send-btn"
        :disabled="!inputText.trim()"
        title="发送 (Enter)"
        @click="send"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M1 1.5l14 6.5-14 6.5v-5l8-1.5-8-1.5z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { ChatMode, AgentSkill } from '../../service/chatService'

const props = defineProps<{
  currentMode: ChatMode
  allowedModes: ChatMode[]
  skills: AgentSkill[]
  selectedSkills: string[]
  isStreaming: boolean
}>()

const emit = defineEmits<{
  'send': [text: string]
  'stop': []
  'mode-change': [mode: ChatMode]
  'skill-toggle': [skillId: string]
}>()

const inputRef = ref<HTMLTextAreaElement | null>(null)
const inputText = ref('')
const showSkillDropdown = ref(false)

const modeLabels: Record<ChatMode, { label: string; desc: string }> = {
  chat: { label: '对话', desc: '自由对话，纯 LLM 问答' },
  quick: { label: '快速', desc: '⚡ 快速分析 (tech + intel → decision)' },
  deep: { label: '深度', desc: '🔬 深度分析，含辩论 + 策略评估' },
  plan: { label: '计划', desc: '📋 先生成计划后执行' }
}

const availableModes = computed(() =>
  props.allowedModes.map(id => ({ id, ...modeLabels[id] }))
)

const selectedSkillName = computed(() => {
  if (props.selectedSkills.length === 0) return ''
  const skill = props.skills.find(s => s.id === props.selectedSkills[0])
  return skill?.name || ''
})

const placeholder = computed(() => {
  switch (props.currentMode) {
    case 'chat': return '输入问题...'
    case 'quick': return '输入股票代码，快速分析...'
    case 'deep': return '输入标的进行深度分析...'
    case 'plan': return '描述分析目标...'
    default: return '输入问题...'
  }
})

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function send() {
  const text = inputText.value.trim()
  if (!text) return

  // 斜杠命令解析
  if (text.startsWith('/mode ')) {
    const mode = text.slice(6).trim() as ChatMode
    if (props.allowedModes.includes(mode)) {
      emit('mode-change', mode)
    }
    inputText.value = ''
    return
  }

  emit('send', text)
  inputText.value = ''
  nextTick(() => autoResize())
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function focus() {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
.chat-input-area {
  border-top: 1px solid #333;
  padding: 8px;
  background: #1a1a1a;
}

.chat-input-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mode-selector {
  display: flex;
  gap: 2px;
  background: #252525;
  border-radius: 6px;
  padding: 2px;
}

.mode-btn {
  background: none;
  border: none;
  border-radius: 4px;
  color: #888;
  font-size: 11px;
  padding: 3px 8px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.mode-btn:hover {
  color: #ccc;
  background: #333;
}

.mode-btn.active {
  background: #0e639c;
  color: #fff;
}

.skill-selector {
  position: relative;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  background: #252525;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  color: #aaa;
}

.skill-selector:hover {
  background: #333;
}

.skill-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 4px;
  background: #2d2d2d;
  border: 1px solid #444;
  border-radius: 8px;
  padding: 4px;
  min-width: 160px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

.skill-option {
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  color: #ccc;
  cursor: pointer;
}

.skill-option:hover {
  background: #3a3a3a;
}

.skill-option.selected {
  background: #1a3a5c;
  color: #7ec8e3;
}

.chat-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  background: #252525;
  border: 1px solid #3a3a3a;
  border-radius: 10px;
  padding: 6px 10px;
  transition: border-color 0.2s;
}

.chat-input-wrapper:focus-within {
  border-color: #0e639c;
}

.chat-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: #e0e0e0;
  font-size: 13px;
  line-height: 1.4;
  resize: none;
  max-height: 120px;
  font-family: inherit;
}

.chat-input::placeholder {
  color: #666;
}

.chat-send-btn,
.chat-stop-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}

.chat-send-btn {
  background: #0e639c;
  color: #fff;
}

.chat-send-btn:hover:not(:disabled) {
  background: #1177bb;
}

.chat-send-btn:disabled {
  background: #333;
  color: #666;
  cursor: not-allowed;
}

.chat-stop-btn {
  background: #a83232;
  color: #fff;
  font-size: 10px;
}

.chat-stop-btn:hover {
  background: #c43c3c;
}
</style>
