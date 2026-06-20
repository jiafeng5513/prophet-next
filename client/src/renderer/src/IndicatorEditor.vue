<template>
  <div class="indicator-editor">
    <!-- 左侧文件树 -->
    <div class="sidebar" :style="{ width: sidebarWidth + 'px' }">
      <FileTree
        :indicators="indicators"
        :currentId="currentId"
        @select="selectIndicator"
        @create="handleCreate"
        @delete="handleDelete"
        @rename="handleRename"
        @duplicate="handleDuplicate"
      />
    </div>

    <!-- 拖拽分割线 -->
    <div class="resize-handle" @mousedown="startResize"></div>

    <!-- 右侧编辑器区域 -->
    <div class="editor-area">
      <!-- 标签栏 -->
      <div class="editor-tabs" v-if="currentId">
        <div class="tab active">
          <span>{{ currentIndicator?.name || currentId }} / index.js</span>
        </div>
      </div>

      <!-- 编辑器 -->
      <EditorPane
        ref="editorPane"
        :fileId="currentId"
        :code="currentCode"
        @change="onCodeChange"
        @save="saveAndApply"
      />

      <!-- 底部工具栏 -->
      <Toolbar
        :status="status"
        :fileName="currentIndicator?.name || ''"
        :hasFile="!!currentId"
        @validate="validateCode"
        @apply="saveAndApply"
        @open-external="openExternal"
      />
    </div>

    <!-- 新建对话框 -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>新建自定义指标</h3>
        <div class="form-group">
          <label>名称</label>
          <input v-model="newName" placeholder="例如: My Custom RSI" @keyup.enter="confirmCreate" />
        </div>
        <div class="form-group">
          <label>ID（目录名）</label>
          <input v-model="newId" placeholder="例如: my-custom-rsi" @keyup.enter="confirmCreate" />
          <span class="hint">只允许小写字母、数字和连字符</span>
        </div>
        <div class="form-group">
          <label>类型</label>
          <div class="radio-group">
            <label class="radio-label">
              <input type="radio" v-model="newType" value="overlay" /> 主图叠加
            </label>
            <label class="radio-label">
              <input type="radio" v-model="newType" value="subplot" /> 副图
            </label>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn-action secondary" @click="showCreateDialog = false">取消</button>
          <button class="btn-action" @click="confirmCreate" :disabled="!newName || !newId">创建</button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="showDeleteDialog = false">
      <div class="dialog">
        <h3>确认删除</h3>
        <p class="dialog-message">确定要删除指标 <strong>{{ deleteTarget?.name }}</strong> 吗？此操作不可恢复。</p>
        <div class="dialog-actions">
          <button class="btn-action secondary" @click="showDeleteDialog = false">取消</button>
          <button class="btn-action danger" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import FileTree from './components/indicator-editor/FileTree.vue'
import EditorPane from './components/indicator-editor/EditorPane.vue'
import Toolbar from './components/indicator-editor/Toolbar.vue'
import { validateInWorker } from './service/indicatorSandbox'

// State
const indicators = ref([])
const currentId = ref(null)
const currentIndicator = ref(null)
const currentCode = ref('')
const sidebarWidth = ref(220)
const status = ref('idle') // idle | ok | error | modified
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const newName = ref('')
const newId = ref('')
const newType = ref('overlay')

const editorPane = ref(null)

// API
const api = window.indicatorEditorAPI

onMounted(async () => {
  await loadIndicators()

  // URL 参数导航
  const params = new URLSearchParams(window.location.search)
  const initialId = params.get('indicatorId')
  if (initialId && indicators.value.find((i) => i.id === initialId)) {
    selectIndicator(initialId)
  }

  // 外部文件变化同步
  api.onFileChanged(({ id, code }) => {
    if (id === currentId.value) {
      currentCode.value = code
      status.value = 'ok'
    }
    loadIndicators()
  })

  api.onNavigateTo(({ id }) => {
    selectIndicator(id)
  })

  api.onReloadResult(({ id, success, error }) => {
    if (id === currentId.value) {
      status.value = success ? 'ok' : 'error'
    }
  })
})

async function loadIndicators() {
  indicators.value = await api.listIndicators()
}

async function selectIndicator(id) {
  currentId.value = id
  const data = await api.readIndicator(id)
  if (!data) {
    status.value = 'error'
    return
  }
  currentIndicator.value = data.manifest
  currentCode.value = data.code
  status.value = 'idle'
}

function onCodeChange(code) {
  currentCode.value = code
  status.value = 'modified'
}

async function saveAndApply() {
  if (!currentId.value) return
  const code = editorPane.value?.getCode() || currentCode.value
  const result = await api.saveIndicator(currentId.value, code, currentIndicator.value)
  status.value = result.success ? 'ok' : 'error'
}

async function validateCode() {
  const code = editorPane.value?.getCode() || currentCode.value
  const result = await validateInWorker(code)
  status.value = result.success ? 'ok' : 'error'
}

async function openExternal() {
  if (!currentId.value) return
  await api.openExternal(currentId.value)
}

// Create
function handleCreate() {
  newName.value = ''
  newId.value = ''
  newType.value = 'overlay'
  showCreateDialog.value = true
}

async function confirmCreate() {
  if (!newName.value || !newId.value) return
  const result = await api.createIndicator(newName.value, newId.value, { overlay: newType.value === 'overlay' })
  if (result.success) {
    showCreateDialog.value = false
    await loadIndicators()
    selectIndicator(newId.value)
  }
}

watch(newName, (name) => {
  if (!name) { newId.value = ''; return }
  newId.value = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
})

// Delete
function handleDelete(id) {
  const ind = indicators.value.find((i) => i.id === id)
  deleteTarget.value = ind || { id, name: id }
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  const result = await api.deleteIndicator(deleteTarget.value.id)
  if (result.success) {
    showDeleteDialog.value = false
    if (currentId.value === deleteTarget.value.id) {
      currentId.value = null
      currentCode.value = ''
      currentIndicator.value = null
    }
    await loadIndicators()
  }
}

// Rename
function handleRename(item) {
  const newNameStr = prompt('输入新名称:', item.name)
  if (newNameStr && newNameStr !== item.name) {
    api.readIndicator(item.id).then((data) => {
      if (data) {
        const manifest = { ...data.manifest, name: newNameStr }
        api.saveIndicator(item.id, data.code, manifest).then(() => loadIndicators())
      }
    })
  }
}

// Duplicate
async function handleDuplicate(item) {
  const dupId = item.id + '-copy'
  const data = await api.readIndicator(item.id)
  if (!data) return
  const result = await api.createIndicator(item.name + ' (Copy)', dupId, { overlay: data.manifest.overlay })
  if (result.success) {
    await api.saveIndicator(dupId, data.code, { ...data.manifest, id: dupId, name: item.name + ' (Copy)' })
    await loadIndicators()
    selectIndicator(dupId)
  }
}

// Resize
function startResize(e) {
  const startX = e.clientX
  const startWidth = sidebarWidth.value
  function onMouseMove(e) {
    sidebarWidth.value = Math.max(150, Math.min(400, startWidth + (e.clientX - startX)))
  }
  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.indicator-editor {
  display: flex;
  height: 100vh;
  color: #ccc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.sidebar {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.resize-handle {
  width: 4px;
  cursor: col-resize;
  background: #252526;
  transition: background 0.2s;
}

.resize-handle:hover {
  background: #007acc;
}

.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #1e1e1e;
}

.editor-tabs {
  display: flex;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
  height: 35px;
  align-items: center;
}

.tab {
  padding: 0 16px;
  font-size: 13px;
  color: #999;
  height: 100%;
  display: flex;
  align-items: center;
  border-bottom: 2px solid transparent;
}

.tab.active {
  color: #fff;
  border-bottom-color: #007acc;
  background: #1e1e1e;
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #2d2d2d;
  border: 1px solid #3c3c3c;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.dialog h3 {
  margin: 0 0 16px;
  color: #ddd;
  font-weight: 500;
}

.dialog-message {
  color: #ccc;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.form-group input[type="text"],
.form-group input:not([type]) {
  width: 100%;
  padding: 8px 10px;
  background: #3c3c3c;
  border: 1px solid #555;
  border-radius: 4px;
  color: #ddd;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.form-group input:focus {
  border-color: #007acc;
}

.radio-group {
  display: flex;
  gap: 16px;
  margin-top: 4px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #ccc;
  cursor: pointer;
}

.hint {
  font-size: 11px;
  color: #666;
  margin-top: 4px;
  display: block;
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn-action {
  background: #0e639c;
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
}

.btn-action:hover:not(:disabled) {
  background: #1177bb;
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-action.secondary {
  background: #3c3c3c;
}

.btn-action.secondary:hover {
  background: #4c4c4c;
}

.btn-action.danger {
  background: #a1260d;
}

.btn-action.danger:hover {
  background: #c62d16;
}
</style>
