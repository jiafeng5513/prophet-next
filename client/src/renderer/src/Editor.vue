<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import 'monaco-editor/esm/vs/basic-languages/python/python.contribution'

const editorEl = ref(null)
let editorInstance = null
let currentFilePath = null

onMounted(() => {
  // 1) 注册一次性的 Snippets（幂等保护，避免 HMR 重复注册）
  if (!window.__pythonSnippetsRegistered) {
    monaco.languages.registerCompletionItemProvider('python', {
      provideCompletionItems: () => ({
        suggestions: [
          {
            label: 'def',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: ['def ${1:name}(${2:args}):', '    ${3:pass}'].join('\n'),
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
          },
          {
            label: 'ifmain',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: ['if __name__ == "__main__":', '    ${1:main()}'].join('\n'),
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
          }
        ]
      })
    })
    window.__pythonSnippetsRegistered = true
  }

  // 2) 可选：极简“格式化器”（示例：去除行尾空格）
  if (!window.__pythonFormatterRegistered) {
    monaco.languages.registerDocumentFormattingEditProvider('python', {
      provideDocumentFormattingEdits(model) {
        const text = model.getValue()
        const formatted = text
          .split('\n')
          .map((l) => l.replace(/[ \t]+$/g, '')) // 仅示例：删掉行尾空白
          .join('\n')
        return [
          {
            range: model.getFullModelRange(),
            text: formatted
          }
        ]
      }
    })
    window.__pythonFormatterRegistered = true
  }

  // 3) 创建编辑器
  editorInstance = monaco.editor.create(editorEl.value, {
    value: '',
    language: 'python',
    theme: 'vs-dark',
    fontSize: 14,
    automaticLayout: true,
    minimap: { enabled: false }
  })

  // 4) 监听主进程发来的打开文件消息
  if (window.electronAPI && window.electronAPI.onOpenFileInEditor) {
    window.electronAPI.onOpenFileInEditor(async (filePath) => {
      console.log('[Editor] 收到打开文件请求:', filePath)
      if (window.electronAPI.readFile) {
        const content = await window.electronAPI.readFile(filePath)
        if (content !== null && editorInstance) {
          editorInstance.setValue(content)
          currentFilePath = filePath
        }
      }
    })
  }
})

onBeforeUnmount(() => {
  if (editorInstance) {
    editorInstance.dispose()
    editorInstance = null
  }
})
</script>
<template>
  <div class="editor-page">
    <div ref="editorEl" class="editor-root"></div>
  </div>
</template>

<style scoped>
.editor-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  background: #0f172a;
  overflow: hidden;
  display: block;
}

.editor-root {
  position: absolute;
  inset: 0;
  /* top:0; right:0; bottom:0; left:0 */
}
</style>
