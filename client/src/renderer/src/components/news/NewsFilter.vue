<template>
  <div class="news-filter">
    <div class="filter-inputs">
      <input
        class="filter-input"
        type="text"
        placeholder="搜索关键词..."
        :value="modelValue.keyword"
        @input="updateField('keyword', $event.target.value)"
        @keyup.enter="updateField('keyword', $event.target.value)"
      />
      <input
        class="filter-input"
        type="text"
        placeholder="股票代码"
        :value="modelValue.code"
        @input="updateField('code', $event.target.value)"
        @keyup.enter="updateField('code', $event.target.value)"
      />
    </div>
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

const emit = defineEmits(['update:modelValue'])

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
  flex-direction: column;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #333;
  gap: 6px;
  flex-shrink: 0;
}

.filter-inputs {
  display: flex;
  gap: 6px;
}

.filter-input {
  flex: 1;
  min-width: 0;
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 4px;
  color: #e0e0e0;
  padding: 5px 8px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.filter-input:focus {
  border-color: #4a9eff;
}

.filter-input::placeholder {
  color: #666;
}

.time-range {
  display: flex;
  gap: 2px;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 2px;
}

.time-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #999;
  padding: 3px 0;
  font-size: 11px;
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
</style>
