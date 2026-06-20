<template>
  <div class="search-bar" ref="searchBarRef">
    <span class="search-icon">🔍</span>
    <input
      ref="inputRef"
      :value="modelValue"
      type="text"
      class="search-input"
      placeholder="代码/名称/拼音首字母..."
      @input="onInput"
      @keydown.escape="$emit('clear')"
      @keydown.enter="onEnterSearch"
      @focus="showHistory = !modelValue && history.length > 0"
      @blur="hideHistoryDelayed"
    />
    <span v-if="loading" class="search-spinner"></span>
    <button
      v-else-if="modelValue"
      class="clear-btn"
      title="清除搜索"
      @click="$emit('clear')"
    >×</button>
    <button
      v-if="!loading"
      class="search-btn"
      title="搜索"
      @click="onClickSearch"
    >⏎</button>

    <!-- 搜索历史下拉 -->
    <div v-if="showHistory && history.length > 0" class="search-history">
      <div class="history-header">
        <span>搜索历史</span>
        <button class="history-clear-btn" @mousedown.prevent="clearHistory">清空</button>
      </div>
      <div
        v-for="(item, i) in history"
        :key="i"
        class="history-item"
        @mousedown.prevent="selectHistory(item)"
      >{{ item }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const HISTORY_KEY = 'symbol-search-history'
const MAX_HISTORY = 10

const props = defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])

const inputRef = ref(null)
const searchBarRef = ref(null)
const showHistory = ref(false)
const history = ref([])

function loadHistory() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY)
    history.value = saved ? JSON.parse(saved) : []
  } catch {
    history.value = []
  }
}

function saveHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}

function addToHistory(query) {
  if (!query || query.trim().length === 0) return
  const q = query.trim()
  history.value = [q, ...history.value.filter((h) => h !== q)].slice(0, MAX_HISTORY)
  saveHistory()
}

function clearHistory() {
  history.value = []
  localStorage.removeItem(HISTORY_KEY)
  showHistory.value = false
}

function selectHistory(item) {
  emit('update:modelValue', item)
  emit('search', item)
  showHistory.value = false
}

function onInput(e) {
  const val = e.target.value
  emit('update:modelValue', val)
  showHistory.value = false
}

function onEnterSearch() {
  if (props.modelValue && props.modelValue.trim()) {
    addToHistory(props.modelValue)
    emit('search', props.modelValue)
  }
}

function onClickSearch() {
  if (props.modelValue && props.modelValue.trim()) {
    addToHistory(props.modelValue)
    emit('search', props.modelValue)
  }
}

function hideHistoryDelayed() {
  setTimeout(() => {
    showHistory.value = false
  }, 150)
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  background: #3c3c3c;
  border: 1px solid #555;
  border-radius: 4px;
  padding: 0 8px;
  transition: border-color 0.15s;
  position: relative;
}

.search-bar:focus-within {
  border-color: #0e639c;
}

.search-icon {
  font-size: 12px;
  flex-shrink: 0;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #ccc;
  font-size: 12px;
  padding: 5px 6px;
}

.search-input::placeholder {
  color: #777;
}

.clear-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}

.clear-btn:hover {
  color: #ccc;
}

.search-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 14px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  flex-shrink: 0;
}

.search-btn:hover {
  color: #0e639c;
}

.search-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #555;
  border-top-color: #0e639c;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 搜索历史 */
.search-history {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #2d2d2d;
  border: 1px solid #454545;
  border-radius: 0 0 4px 4px;
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  font-size: 11px;
  color: #888;
  border-bottom: 1px solid #3a3a3a;
}

.history-clear-btn {
  background: none;
  border: none;
  color: #666;
  font-size: 11px;
  cursor: pointer;
  padding: 0;
}

.history-clear-btn:hover {
  color: #0e639c;
}

.history-item {
  padding: 5px 8px;
  font-size: 12px;
  color: #ccc;
  cursor: pointer;
}

.history-item:hover {
  background: #094771;
  color: #fff;
}
</style>
