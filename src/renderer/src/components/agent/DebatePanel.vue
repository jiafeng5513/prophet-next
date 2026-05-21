<template>
  <div class="debate-panel">
    <div class="debate-panel__header">
      <span class="debate-title">多空辩论</span>
      <span class="debate-round">第 {{ debate.round }}/{{ debate.totalRounds }} 轮</span>
      <span class="debate-status" :class="`status-${debate.status}`">
        {{ debate.status === 'running' ? '进行中' : '已完成' }}
      </span>
    </div>

    <div class="debate-panel__content">
      <!-- Bull -->
      <div class="debate-side debate-side--bull" v-if="debate.bull">
        <div class="debate-side__header">
          <span class="debate-side__icon">🐂</span>
          <span class="debate-side__label">Bull Researcher</span>
        </div>
        <div class="debate-side__body" :class="{ collapsed: !bullExpanded }">
          <div class="debate-side__text" v-html="renderedBull"></div>
        </div>
        <button v-if="debate.bull.length > 200" class="debate-toggle" @click="bullExpanded = !bullExpanded">
          {{ bullExpanded ? '收起' : '展开' }}
        </button>
      </div>

      <!-- Bear -->
      <div class="debate-side debate-side--bear" v-if="debate.bear">
        <div class="debate-side__header">
          <span class="debate-side__icon">🐻</span>
          <span class="debate-side__label">Bear Researcher</span>
        </div>
        <div class="debate-side__body" :class="{ collapsed: !bearExpanded }">
          <div class="debate-side__text" v-html="renderedBear"></div>
        </div>
        <button v-if="debate.bear.length > 200" class="debate-toggle" @click="bearExpanded = !bearExpanded">
          {{ bearExpanded ? '收起' : '展开' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { DebateInfo } from '../../service/chatService'

const props = defineProps<{
  debate: DebateInfo
}>()

const bullExpanded = ref(true)
const bearExpanded = ref(true)

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedBull = computed(() => props.debate.bull ? md.render(props.debate.bull) : '')
const renderedBear = computed(() => props.debate.bear ? md.render(props.debate.bear) : '')
</script>

<style scoped>
.debate-panel {
  border-radius: 10px;
  background: #1a2634;
  margin-bottom: 12px;
  overflow: hidden;
}

.debate-panel__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #2a3a4a;
}

.debate-title {
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
}

.debate-round {
  font-size: 11px;
  color: #888;
}

.debate-status {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.status-running {
  background: #1a3a5c;
  color: #7ec8e3;
}

.status-completed {
  background: #1b3a2a;
  color: #4ec9b0;
}

.debate-panel__content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.debate-side {
  border-radius: 8px;
  overflow: hidden;
}

.debate-side--bull {
  border-left: 3px solid #22c55e;
  background: #0f2818;
}

.debate-side--bear {
  border-left: 3px solid #ef4444;
  background: #2a0f0f;
}

.debate-side__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
}

.debate-side--bull .debate-side__label { color: #4ade80; }
.debate-side--bear .debate-side__label { color: #f87171; }

.debate-side__body {
  padding: 0 12px 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #d0d0d0;
}

.debate-side__body.collapsed {
  max-height: 80px;
  overflow: hidden;
  position: relative;
}

.debate-side__body.collapsed::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: linear-gradient(transparent, rgba(26, 38, 52, 0.9));
}

.debate-side__text :deep(p) {
  margin: 0 0 6px;
}

.debate-toggle {
  display: block;
  width: 100%;
  background: none;
  border: none;
  border-top: 1px solid #2a3a4a;
  color: #7ec8e3;
  font-size: 11px;
  padding: 6px;
  cursor: pointer;
}

.debate-toggle:hover {
  background: rgba(126, 200, 227, 0.1);
}
</style>
