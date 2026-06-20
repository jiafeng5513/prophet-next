<template>
  <div ref="listRef" class="chat-message-list" @scroll="handleScroll">
    <!-- 空状态 -->
    <div v-if="messages.length === 0 && !isStreaming" class="chat-empty">
      <div class="chat-empty__icon">💬</div>
      <div class="chat-empty__title">向 AI 提问</div>
      <div class="chat-empty__desc">输入股票代码或问题，获取智能分析</div>
      <div v-if="quickQuestions.length" class="chat-empty__quick">
        <button
          v-for="q in quickQuestions"
          :key="q.text"
          class="quick-btn"
          @click="$emit('quick-send', q.text, q.skill)"
        >
          {{ q.icon }} {{ q.text }}
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <ChatMessage
      v-for="msg in messages"
      :key="msg.id"
      :message="msg"
    />

    <!-- 流式消息 (正在生成) -->
    <ChatMessage
      v-if="isStreaming && streamingMessage"
      :message="streamingMessage"
      :is-streaming="true"
    />

    <!-- 升级提示 -->
    <div v-if="shouldUpgrade" class="chat-upgrade-hint">
      <button class="upgrade-btn" @click="$emit('upgrade')">
        🚀 启动深度分析
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessage as ChatMessageType } from '../../service/chatService'

const props = defineProps<{
  messages: ChatMessageType[]
  isStreaming: boolean
  streamingMessage?: ChatMessageType | null
  shouldUpgrade?: boolean
  quickQuestions?: { icon: string; text: string; skill?: string }[]
}>()

defineEmits<{
  'quick-send': [text: string, skill?: string]
  'upgrade': []
}>()

const listRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

function scrollToBottom() {
  if (listRef.value && autoScroll.value) {
    nextTick(() => {
      listRef.value!.scrollTop = listRef.value!.scrollHeight
    })
  }
}

function handleScroll() {
  if (!listRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = listRef.value
  autoScroll.value = scrollHeight - scrollTop - clientHeight < 50
}

// 自动滚动到底部
watch(() => props.messages.length, scrollToBottom)
watch(() => props.streamingMessage?.content, scrollToBottom)
</script>

<style scoped>
.chat-message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  scrollbar-width: thin;
  scrollbar-color: #444 transparent;
}

.chat-message-list::-webkit-scrollbar {
  width: 5px;
}

.chat-message-list::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 3px;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  padding: 20px;
}

.chat-empty__icon {
  font-size: 36px;
  opacity: 0.6;
}

.chat-empty__title {
  font-size: 14px;
  color: #ccc;
  font-weight: 500;
}

.chat-empty__desc {
  font-size: 11px;
  color: #777;
}

.chat-empty__quick {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  width: 100%;
  max-width: 260px;
}

.quick-btn {
  background: #1e2d3d;
  border: 1px solid #2a3f52;
  border-radius: 8px;
  color: #b8d4e8;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, border-color 0.15s;
}

.quick-btn:hover {
  background: #253d52;
  border-color: #3a5f7a;
}

.chat-upgrade-hint {
  display: flex;
  justify-content: center;
  padding: 8px 12px;
}

.upgrade-btn {
  background: linear-gradient(135deg, #1a5276 0%, #0e639c 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.upgrade-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 99, 156, 0.4);
}
</style>
