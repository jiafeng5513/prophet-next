<template>
  <div class="filter-bar">
    <!-- 搜索输入 -->
    <div class="search-box">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
        <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85zm-5.242.156a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"/>
      </svg>
      <input
        type="text"
        class="search-input"
        :value="searchQuery"
        placeholder="搜索代码或名称..."
        @input="$emit('update:searchQuery', $event.target.value)"
        @keyup.escape="$emit('update:searchQuery', '')"
      />
      <button v-if="searchQuery" class="clear-btn" @click="$emit('update:searchQuery', '')">×</button>
    </div>

    <!-- 活跃筛选条件 -->
    <div v-if="activeFilters.length" class="active-filters">
      <span
        v-for="(filter, idx) in activeFilters"
        :key="idx"
        class="filter-tag"
      >
        {{ filter.label }}
        <button class="tag-remove" @click="$emit('removeFilter', idx)">×</button>
      </span>
      <button class="clear-all" @click="$emit('clearFilters')">清除全部</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  searchQuery: {
    type: String,
    default: ''
  },
  activeFilters: {
    type: Array,
    default: () => []
  }
})

defineEmits(['update:searchQuery', 'removeFilter', 'clearFilters'])
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #1e1e1e;
  border-bottom: 1px solid #333;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #2a2a2c;
  border: 1px solid #3a3a3c;
  border-radius: 4px;
  padding: 4px 8px;
  min-width: 200px;
}

.search-box:focus-within {
  border-color: #4fc3f7;
}

.search-icon {
  color: #888;
  flex-shrink: 0;
}

.search-input {
  background: transparent;
  border: none;
  color: #e0e0e0;
  font-size: 13px;
  outline: none;
  width: 100%;
}

.search-input::placeholder {
  color: #666;
}

.clear-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.clear-btn:hover {
  color: #fff;
}

.active-filters {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: #2a3a4a;
  border: 1px solid #3a5a6a;
  border-radius: 12px;
  font-size: 12px;
  color: #8ec8e8;
}

.tag-remove {
  background: none;
  border: none;
  color: #8ec8e8;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.tag-remove:hover {
  color: #fff;
}

.clear-all {
  background: none;
  border: none;
  color: #888;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
}

.clear-all:hover {
  color: #e0e0e0;
}
</style>
