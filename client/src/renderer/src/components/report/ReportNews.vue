<template>
  <div class="report-news" v-if="items.length > 0">
    <div class="news-header">
      <h3 class="section-title">📰 相关新闻</h3>
      <span class="news-count">{{ items.length }} 条</span>
    </div>
    <div class="news-list">
      <a
        v-for="(item, i) in items"
        :key="i"
        class="news-card"
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <div class="news-title">{{ item.title }}</div>
        <div class="news-snippet" v-if="item.snippet">{{ item.snippet }}</div>
        <div class="news-link">查看详情 →</div>
      </a>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] }
})
</script>

<style scoped>
.report-news {
  margin: 20px 0;
}
.news-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2a2a;
}
.section-title {
  font-size: 16px;
  color: #e0e0e0;
  margin: 0;
}
.news-count {
  font-size: 12px;
  color: #888;
}
.news-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.news-card {
  display: block;
  background: #252526;
  border-radius: 8px;
  padding: 14px 16px;
  text-decoration: none;
  color: inherit;
  border-left: 3px solid transparent;
  transition: border-color 0.15s, background 0.15s;
}
.news-card:hover {
  background: #2a2d2e;
  border-left-color: #4a9eff;
}
.news-title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 6px;
  line-height: 1.4;
}
.news-snippet {
  font-size: 13px;
  color: #999;
  line-height: 1.5;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-link {
  font-size: 12px;
  color: #4a9eff;
}
</style>
