<template>
  <div class="news-detail">
    <!-- 加载中 -->
    <div v-if="loading" class="detail-loading">
      <div class="loading-spinner"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!news" class="detail-empty">
      <div class="empty-icon">👈</div>
      <p>选择左侧新闻查看详情</p>
    </div>

    <!-- 新闻详情 -->
    <div v-else class="detail-content">
      <h1 class="detail-title">{{ news.title }}</h1>

      <div class="detail-meta">
        <span v-if="news.source" class="meta-source">{{ news.source }}</span>
        <span v-if="news.published_date" class="meta-time">{{ formatDateTime(news.published_date) }}</span>
        <span v-if="news.code" class="meta-stock">
          {{ news.name || news.code }}
          <span v-if="news.name && news.code" class="meta-code">({{ news.code }})</span>
        </span>
      </div>

      <div v-if="news.dimension" class="detail-dimension">
        <span class="dimension-tag">{{ dimensionLabel(news.dimension) }}</span>
      </div>

      <div class="detail-body">
        <p class="detail-snippet">{{ news.snippet || '暂无摘要内容' }}</p>
      </div>

      <div v-if="news.provider || news.query" class="detail-extra">
        <div v-if="news.provider" class="extra-item">
          <span class="extra-label">数据来源</span>
          <span class="extra-value">{{ news.provider }}</span>
        </div>
        <div v-if="news.query" class="extra-item">
          <span class="extra-label">搜索关键词</span>
          <span class="extra-value">{{ news.query }}</span>
        </div>
        <div v-if="news.fetched_at" class="extra-item">
          <span class="extra-label">入库时间</span>
          <span class="extra-value">{{ formatDateTime(news.fetched_at) }}</span>
        </div>
      </div>

      <div v-if="news.url" class="detail-actions">
        <a class="btn-view-original" :href="news.url" target="_blank" rel="noopener noreferrer" @click.prevent="openUrl(news.url)">
          查看原文 ↗
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  news: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

function formatDateTime(str) {
  if (!str) return ''
  // "2026-04-25 10:30:00" -> "2026年4月25日 10:30"
  try {
    const dt = new Date(str.replace(' ', 'T'))
    if (isNaN(dt.getTime())) return str
    const y = dt.getFullYear()
    const m = dt.getMonth() + 1
    const d = dt.getDate()
    const h = String(dt.getHours()).padStart(2, '0')
    const min = String(dt.getMinutes()).padStart(2, '0')
    return `${y}年${m}月${d}日 ${h}:${min}`
  } catch {
    return str
  }
}

function dimensionLabel(dim) {
  const map = {
    latest_news: '最新动态',
    risk_check: '风险检查',
    earnings: '财报',
    market_analysis: '市场分析',
    industry: '行业动态'
  }
  return map[dim] || dim
}

function openUrl(url) {
  if (window.electronAPI && window.electronAPI.openExternal) {
    window.electronAPI.openExternal(url)
  } else {
    window.open(url, '_blank')
  }
}
</script>

<style scoped>
.news-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-loading,
.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #777;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.detail-content {
  padding: 32px 40px;
  max-width: 800px;
}

.detail-title {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.4;
  color: #fff;
  margin: 0 0 16px 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #999;
  margin-bottom: 12px;
}

.meta-source {
  color: #4a9eff;
  font-weight: 500;
}

.meta-stock {
  background: #2a2d2e;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.meta-code {
  color: #777;
}

.detail-dimension {
  margin-bottom: 20px;
}

.dimension-tag {
  display: inline-block;
  padding: 2px 10px;
  background: rgba(74, 158, 255, 0.15);
  color: #4a9eff;
  border-radius: 4px;
  font-size: 12px;
}

.detail-body {
  margin: 24px 0;
  padding: 20px 0;
  border-top: 1px solid #333;
  border-bottom: 1px solid #333;
}

.detail-snippet {
  font-size: 15px;
  line-height: 1.8;
  color: #ccc;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-extra {
  margin: 20px 0;
  padding: 16px;
  background: #252526;
  border-radius: 8px;
}

.extra-item {
  display: flex;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}

.extra-label {
  color: #777;
  width: 80px;
  flex-shrink: 0;
}

.extra-value {
  color: #aaa;
}

.detail-actions {
  margin-top: 24px;
}

.btn-view-original {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 20px;
  background: #4a9eff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-view-original:hover {
  background: #3a8eef;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #333;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
