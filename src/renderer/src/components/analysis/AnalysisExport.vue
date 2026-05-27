<template>
  <div class="analysis-export">
    <button class="export-btn" @click="showMenu = !showMenu">
      📤 导出
    </button>
    <div class="export-menu" v-if="showMenu">
      <button class="export-option" @click="exportPDF">📄 PDF 报告</button>
      <button class="export-option" @click="exportMarkdown">📝 Markdown</button>
      <button class="export-option" @click="copyToClipboard">📋 复制文本</button>
      <button class="export-option" @click="exportJSON">💾 JSON 数据</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { DashboardData } from '../../service/chatService'

const props = defineProps<{
  dashboard: DashboardData
  stockCode: string
  stockName?: string
}>()

const showMenu = ref(false)

function buildMarkdownReport(): string {
  const d = props.dashboard
  const lines: string[] = []

  lines.push(`# ${props.stockCode}${props.stockName ? ' ' + props.stockName : ''} 分析报告`)
  lines.push('')
  lines.push(`**信号**: ${d.signal || '-'} | **置信度**: ${((d.confidence || 0) * 100).toFixed(0)}%`)
  lines.push('')

  if (d.summary) {
    lines.push(`## 核心结论`)
    lines.push(d.summary)
    lines.push('')
  }

  if (d.market_context) {
    const mc = d.market_context
    lines.push(`## 市场环境`)
    if (mc.trend) lines.push(`- 趋势: ${mc.trend}`)
    if (mc.strength) lines.push(`- 强度: ${mc.strength}`)
    if (mc.sentiment) lines.push(`- 情绪: ${mc.sentiment}`)
    lines.push('')
  }

  if (d.debate_summary) {
    const ds = d.debate_summary
    lines.push(`## 多空辩论`)
    if (ds.bull_core_thesis) lines.push(`- 📈 多方: ${ds.bull_core_thesis}`)
    if (ds.bear_core_thesis) lines.push(`- 📉 空方: ${ds.bear_core_thesis}`)
    if (ds.manager_verdict) lines.push(`- ⚖️ 裁决: ${ds.manager_verdict}`)
    lines.push('')
  }

  if (d.risk_assessment) {
    const ra = d.risk_assessment
    lines.push(`## 风险评估`)
    if (ra.aggressive_view) lines.push(`- 🔥 激进: ${ra.aggressive_view}`)
    if (ra.conservative_view) lines.push(`- 🛡️ 保守: ${ra.conservative_view}`)
    if (ra.verdict) lines.push(`- ⚖️ 裁决: ${ra.verdict}`)
    if (ra.max_acceptable_position) lines.push(`- 建议仓位: ${ra.max_acceptable_position}`)
    lines.push('')
  }

  if (d.skill_opinions?.length) {
    lines.push(`## 策略观点`)
    d.skill_opinions.forEach(op => {
      lines.push(`- **${op.skill_name}**: ${op.signal} — ${op.observation || ''}`)
    })
    lines.push('')
  }

  // 相关新闻
  const newsItems = d.intelligence?.key_news || d.key_news
  if (Array.isArray(newsItems) && newsItems.length) {
    lines.push(`## 相关新闻`)
    newsItems.forEach((item: any) => {
      const prefix = item.impact === 'positive' ? '🟢' : item.impact === 'negative' ? '🔴' : '⚪'
      const link = item.url ? ` [链接](${item.url})` : ''
      lines.push(`- ${prefix} ${item.title}${link}`)
    })
    lines.push('')
  }

  lines.push(`---`)
  lines.push(`*生成时间: ${new Date().toLocaleString('zh-CN')}*`)

  return lines.join('\n')
}

function exportMarkdown() {
  const content = buildMarkdownReport()
  downloadFile(`${props.stockCode}_analysis.md`, content, 'text/markdown')
  showMenu.value = false
}

async function exportPDF() {
  const markdown = buildMarkdownReport()
  const html = buildPDFHtml(markdown)
  if (window.electronAPI?.exportPDF) {
    await window.electronAPI.exportPDF(html, `${props.stockCode}_analysis.pdf`)
  } else {
    // 浏览器环境 fallback: 打开新窗口打印
    const w = window.open('', '_blank')
    if (w) {
      w.document.write(html)
      w.document.close()
      w.print()
    }
  }
  showMenu.value = false
}

function buildPDFHtml(markdown: string): string {
  // 简单的 Markdown → HTML 转换（仅处理常用标记）
  let body = markdown
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^- \*\*(.+?)\*\*: (.+)$/gm, '<li><strong>$1</strong>: $2</li>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')

  return `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; padding: 40px; color: #333; line-height: 1.8; }
  h1 { font-size: 20px; border-bottom: 2px solid #1890ff; padding-bottom: 8px; }
  h2 { font-size: 16px; color: #1890ff; margin-top: 20px; }
  li { margin: 4px 0; list-style: disc; margin-left: 20px; }
  hr { border: none; border-top: 1px solid #eee; margin: 16px 0; }
  em { color: #888; font-size: 12px; }
</style></head><body>${body}</body></html>`
}

async function copyToClipboard() {
  const content = buildMarkdownReport()
  try {
    await navigator.clipboard.writeText(content)
  } catch {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = content
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  showMenu.value = false
}

function exportJSON() {
  const content = JSON.stringify(props.dashboard, null, 2)
  downloadFile(`${props.stockCode}_dashboard.json`, content, 'application/json')
  showMenu.value = false
}

function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.analysis-export {
  position: relative;
  display: inline-block;
}

.export-btn {
  background: #253d52;
  border: 1px solid #3a5f7a;
  border-radius: 6px;
  color: #b8d4e8;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.export-btn:hover {
  background: #2d4f6a;
}

.export-menu {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 4px;
  background: #2d2d2d;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
  z-index: 50;
  min-width: 140px;
}

.export-option {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  color: #ccc;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background 0.1s;
}

.export-option:hover {
  background: #37373d;
}

.export-option + .export-option {
  border-top: 1px solid #3a3a3a;
}
</style>
