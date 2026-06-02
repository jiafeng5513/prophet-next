<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <span v-if="status === 'ok'" class="status ok">✓ 已保存</span>
      <span v-else-if="status === 'error'" class="status error">✗ 错误</span>
      <span v-else-if="status === 'modified'" class="status modified">● 已修改</span>
      <span v-else class="status idle">—</span>
      <span v-if="fileName" class="file-label">{{ fileName }}</span>
    </div>
    <div class="toolbar-right">
      <button class="btn" @click="$emit('validate')" :disabled="!hasFile" title="语法验证">
        验证
      </button>
      <button class="btn primary" @click="$emit('apply')" :disabled="!hasFile" title="保存并应用 (Ctrl+S)">
        应用
      </button>
      <button class="btn" @click="$emit('open-external')" :disabled="!hasFile" title="在外部编辑器中打开">
        外部编辑
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: 'idle' }, // idle | ok | error | modified
  fileName: { type: String, default: '' },
  hasFile: { type: Boolean, default: false }
})

defineEmits(['validate', 'apply', 'open-external'])
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #252526;
  border-top: 1px solid #3c3c3c;
  min-height: 36px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 3px;
}

.status.ok {
  color: #4ec9b0;
}

.status.error {
  color: #f48771;
}

.status.modified {
  color: #dcdcaa;
}

.status.idle {
  color: #666;
}

.file-label {
  font-size: 12px;
  color: #999;
}

.btn {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid #555;
  border-radius: 3px;
  background: #333;
  color: #ccc;
  cursor: pointer;
}

.btn:hover:not(:disabled) {
  background: #3c3c3c;
  color: #fff;
}

.btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.btn.primary {
  background: #0e639c;
  border-color: #1177bb;
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  background: #1177bb;
}
</style>
