<template>
  <div class="news-filter">
    <div class="filter-left">
      <input
        class="filter-input keyword-input"
        type="text"
        placeholder="搜索关键词..."
        :value="modelValue.keyword"
        @input="updateField('keyword', $event.target.value)"
        @keyup.enter="updateField('keyword', $event.target.value)"
      />
      <input
        class="filter-input code-input"
        type="text"
        placeholder="股票代码"
        :value="modelValue.code"
        @input="updateField('code', $event.target.value)"
        @keyup.enter="updateField('code', $event.target.value)"
      />
    </div>

    <div class="filter-right">
      <div class="time-range">
        <button
          v-for="opt in timeOptions"
          :key="opt.value"
          class="time-btn"
          :class="{ active: modelValue.days === opt.value }"
          @click="updateField('days', opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>

      <button class="refresh-btn" :disabled="loading" @click="$emit('refresh')">
        <span class="refresh-icon" :class="{ spinning: loading }">⟳</span>
        刷新
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ keyword: '', code: '', days: 7 })
  },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'refresh'])

const timeOptions = [
  { label: '今天', value: 1 },
  { label: '3天', value: 3 },
  { label: '7天', value: 7 },
  { label: '30天', value: 30 }
]

let debounceTimer = null

function updateField(field, value) {
  clearTimeout(debounceTimer)
  // 对文本输入做防抖
  if (field === 'keyword' || field === 'code') {
    debounceTimer = setTimeout(() => {
      emit('update:modelValue', { ...props.modelValue, [field]: value })
    }, 500)
  } else {
    emit('update:modelValue', { ...props.modelValue, [field]: value })
  }
}
</script>

<style scoped>
.news-filter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #252526;
  border-bottom: 1px solid #333;
  gap: 12px;
  flex-shrink: 0;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-input {
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 4px;
  color: #e0e0e0;
  padding: 6px 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.filter-input:focus {
  border-color: #4a9eff;
}

.filter-input::placeholder {
  color: #666;
}

.keyword-input {
  width: 180px;
}

.code-input {
  width: 100px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-range {
  display: flex;
  gap: 2px;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 2px;
}

.time-btn {
  background: transparent;
  border: none;
  color: #999;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s;
}

.time-btn:hover {
  color: #e0e0e0;
}

.time-btn.active {
  background: #4a9eff;
  color: #fff;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: 1px solid #555;
  color: #ccc;
  padding: 5px 12px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.refresh-btn:hover:not(:disabled) {
  border-color: #4a9eff;
  color: #4a9eff;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-icon {
  font-size: 16px;
  display: inline-block;
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
