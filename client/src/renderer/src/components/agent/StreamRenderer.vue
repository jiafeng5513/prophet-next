<template>
  <div class="stream-renderer" v-html="renderedContent"></div>
  <span v-if="streaming" class="stream-cursor">▎</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedContent = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<style scoped>
.stream-renderer {
  font-size: 13px;
  line-height: 1.6;
  color: #e0e0e0;
}

.stream-renderer :deep(p) {
  margin: 0 0 8px;
}

.stream-renderer :deep(p:last-child) {
  margin-bottom: 0;
}

.stream-renderer :deep(pre) {
  background: #0d1117;
  border-radius: 6px;
  padding: 10px;
  overflow-x: auto;
  font-size: 12px;
}

.stream-renderer :deep(code) {
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
}

.stream-renderer :deep(h1),
.stream-renderer :deep(h2),
.stream-renderer :deep(h3) {
  color: #ffffff;
  margin: 12px 0 6px;
}

.stream-renderer :deep(h2) { font-size: 16px; }
.stream-renderer :deep(h3) { font-size: 14px; }

.stream-renderer :deep(ul),
.stream-renderer :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.stream-renderer :deep(li) {
  margin-bottom: 3px;
}

.stream-renderer :deep(a) {
  color: #4fc1ff;
}

.stream-renderer :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 12px;
}

.stream-renderer :deep(th),
.stream-renderer :deep(td) {
  border: 1px solid #333;
  padding: 4px 8px;
}

.stream-renderer :deep(th) {
  background: #252525;
  color: #ccc;
}

.stream-cursor {
  color: #4fc1ff;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
