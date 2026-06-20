<template>
  <div class="follow-up-input">
    <div class="follow-up-header">💬 追问</div>
    <div class="quick-questions" v-if="quickQuestions.length">
      <button
        v-for="q in quickQuestions"
        :key="q"
        class="quick-q-btn"
        @click="$emit('send', q)"
      >{{ q }}</button>
    </div>
    <div class="input-row">
      <input
        v-model="text"
        class="follow-input"
        placeholder="基于此分析继续追问..."
        @keydown.enter="onSend"
      />
      <button class="send-btn" @click="onSend" :disabled="!text.trim()">↵</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  stockCode?: string
  signal?: string
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const text = ref('')

const quickQuestions = computed(() => {
  const qs: string[] = []
  if (props.signal === 'buy' || props.signal === '买入') {
    qs.push('最佳入场时机是什么？')
    qs.push('如果大盘下跌3%，结论会变吗？')
  } else if (props.signal === 'sell' || props.signal === '卖出') {
    qs.push('卖出后什么条件可以重新买入？')
  }
  qs.push('对比同板块其他龙头')
  qs.push('帮我生成详细交易计划')
  return qs.slice(0, 3)
})

function onSend() {
  const val = text.value.trim()
  if (!val) return
  emit('send', val)
  text.value = ''
}
</script>

<style scoped>
.follow-up-input {
  padding: 10px 12px;
  background: #1e2a36;
  border-radius: 8px;
}

.follow-up-header {
  font-size: 12px;
  font-weight: 600;
  color: #b0c4d8;
  margin-bottom: 8px;
}

.quick-questions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.quick-q-btn {
  background: #253d52;
  border: 1px solid #3a5f7a;
  border-radius: 4px;
  color: #b8d4e8;
  padding: 5px 10px;
  font-size: 11px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.quick-q-btn:hover {
  background: #2d4f6a;
}

.input-row {
  display: flex;
  gap: 6px;
}

.follow-input {
  flex: 1;
  background: #151f2b;
  border: 1px solid #3a5f7a;
  border-radius: 4px;
  color: #e0e0e0;
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
}

.follow-input:focus {
  border-color: #4a9eff;
}

.follow-input::placeholder {
  color: #555;
}

.send-btn {
  background: #0e639c;
  border: none;
  border-radius: 4px;
  color: #fff;
  width: 30px;
  cursor: pointer;
  font-size: 14px;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
