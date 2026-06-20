<template>
  <div class="editor-pane" ref="containerRef">
    <div v-if="!fileId" class="placeholder">
      <div class="placeholder-content">
        <p>选择一个指标文件开始编辑</p>
        <p class="hint">或点击左侧 + 创建新指标</p>
      </div>
    </div>
    <div v-else class="editor-wrapper" ref="editorRef"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as monaco from 'monaco-editor'

const props = defineProps({
  fileId: { type: String, default: null },
  code: { type: String, default: '' },
  language: { type: String, default: 'javascript' }
})

const emit = defineEmits(['change', 'save'])

const containerRef = ref(null)
const editorRef = ref(null)
let editor = null
let resizeObserver = null

// PineJS API 补全提供者
function registerPineJSCompletions() {
  const pineAPIs = [
    { label: 'PineJS.Std.ema', detail: '(source, length) → number', doc: '指数移动平均' },
    { label: 'PineJS.Std.sma', detail: '(source, length) → number', doc: '简单移动平均' },
    { label: 'PineJS.Std.rsi', detail: '(source, length) → number', doc: '相对强弱指标' },
    { label: 'PineJS.Std.macd', detail: '(source, fast, slow, signal) → [macd, signal, hist]', doc: 'MACD' },
    { label: 'PineJS.Std.close', detail: '→ number', doc: '收盘价' },
    { label: 'PineJS.Std.open', detail: '→ number', doc: '开盘价' },
    { label: 'PineJS.Std.high', detail: '→ number', doc: '最高价' },
    { label: 'PineJS.Std.low', detail: '→ number', doc: '最低价' },
    { label: 'PineJS.Std.volume', detail: '→ number', doc: '成交量' },
    { label: 'PineJS.Std.hlc3', detail: '→ number', doc: '(最高+最低+收盘)/3' },
    { label: 'PineJS.Std.ohlc4', detail: '→ number', doc: '(开+高+低+收)/4' },
    { label: 'PineJS.Std.hl2', detail: '→ number', doc: '(最高+最低)/2' },
    { label: 'PineJS.Std.tr', detail: '→ number', doc: '真实波幅' },
    { label: 'PineJS.Std.atr', detail: '(length) → number', doc: '平均真实波幅' },
    { label: 'PineJS.Std.stoch', detail: '(source, high, low, length) → number', doc: '随机指标' },
    { label: 'PineJS.Std.bb', detail: '(source, length, mult) → [upper, mid, lower]', doc: '布林带' },
    { label: 'PineJS.Std.wma', detail: '(source, length) → number', doc: '加权移动平均' },
    { label: 'PineJS.Std.vwma', detail: '(source, length) → number', doc: '成交量加权移动平均' },
    { label: 'PineJS.Std.highest', detail: '(source, length) → number', doc: '最高值' },
    { label: 'PineJS.Std.lowest', detail: '(source, length) → number', doc: '最低值' },
    { label: 'PineJS.Std.cross', detail: '(a, b) → boolean', doc: '交叉' },
    { label: 'PineJS.Std.crossover', detail: '(a, b) → boolean', doc: '上穿' },
    { label: 'PineJS.Std.crossunder', detail: '(a, b) → boolean', doc: '下穿' },
  ]

  monaco.languages.registerCompletionItemProvider('javascript', {
    triggerCharacters: ['.'],
    provideCompletionItems(model, position) {
      const textUntilPosition = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      })

      if (!textUntilPosition.match(/PineJS\.Std\.?\w*$/)) {
        return { suggestions: [] }
      }

      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }

      return {
        suggestions: pineAPIs.map((api) => {
          const methodName = api.label.split('.').pop()
          return {
            label: methodName,
            kind: monaco.languages.CompletionItemKind.Method,
            detail: api.detail,
            documentation: api.doc,
            insertText: methodName,
            range,
          }
        }),
      }
    },
  })
}

function createEditor() {
  if (!editorRef.value || editor) return

  editor = monaco.editor.create(editorRef.value, {
    value: props.code,
    language: props.language,
    theme: 'vs-dark',
    fontSize: 13,
    lineNumbers: 'on',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: false,
    tabSize: 2,
    wordWrap: 'on',
    padding: { top: 8 },
    suggestOnTriggerCharacters: true,
  })

  editor.onDidChangeModelContent(() => {
    emit('change', editor.getValue())
  })

  // Ctrl+S 保存
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    emit('save')
  })

  // 响应容器大小变化
  resizeObserver = new ResizeObserver(() => {
    editor?.layout()
  })
  resizeObserver.observe(editorRef.value)
}

function destroyEditor() {
  resizeObserver?.disconnect()
  resizeObserver = null
  editor?.dispose()
  editor = null
}

watch(
  () => props.fileId,
  async (newId) => {
    if (newId) {
      await nextTick()
      if (!editor) {
        createEditor()
      } else {
        editor.setValue(props.code)
      }
    } else {
      destroyEditor()
    }
  }
)

watch(
  () => props.code,
  (newCode) => {
    if (editor && editor.getValue() !== newCode) {
      editor.setValue(newCode)
    }
  }
)

onMounted(() => {
  registerPineJSCompletions()
  if (props.fileId) {
    nextTick(() => createEditor())
  }
})

onBeforeUnmount(() => {
  destroyEditor()
})

defineExpose({
  getCode: () => editor?.getValue() ?? '',
  focus: () => editor?.focus(),
})
</script>

<style scoped>
.editor-pane {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.editor-wrapper {
  position: absolute;
  inset: 0;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e1e1e;
}

.placeholder-content {
  text-align: center;
  color: #666;
  font-size: 14px;
}

.placeholder-content .hint {
  font-size: 12px;
  margin-top: 8px;
  color: #555;
}
</style>
