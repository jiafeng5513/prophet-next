<template>
  <div class="file-tree">
    <div class="tree-header">
      <span class="tree-title">自定义指标</span>
      <button class="btn-icon" @click="$emit('create')" title="新建指标">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
      </button>
    </div>
    <div class="tree-list">
      <div
        v-for="ind in indicators"
        :key="ind.id"
        class="tree-item"
        :class="{ active: currentId === ind.id }"
        @click="$emit('select', ind.id)"
        @contextmenu.prevent="showContextMenu($event, ind)"
      >
        <span class="item-icon">📊</span>
        <span class="item-name">{{ ind.name }}</span>
        <span class="item-version">v{{ ind.version }}</span>
      </div>
      <div v-if="indicators.length === 0" class="empty-hint">
        暂无自定义指标<br />点击 + 创建第一个
      </div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      @mouseleave="contextMenu.visible = false"
    >
      <div class="menu-item" @click="handleRename">重命名</div>
      <div class="menu-item" @click="handleDuplicate">复制</div>
      <div class="menu-item danger" @click="handleDelete">删除</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

defineProps({
  indicators: { type: Array, default: () => [] },
  currentId: { type: String, default: null }
})

const emit = defineEmits(['select', 'create', 'delete', 'rename', 'duplicate'])

const contextMenu = reactive({ visible: false, x: 0, y: 0, item: null })

function showContextMenu(event, item) {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.item = item
}

function handleDelete() {
  contextMenu.visible = false
  if (contextMenu.item) {
    emit('delete', contextMenu.item.id)
  }
}

function handleRename() {
  contextMenu.visible = false
  if (contextMenu.item) {
    emit('rename', contextMenu.item)
  }
}

function handleDuplicate() {
  contextMenu.visible = false
  if (contextMenu.item) {
    emit('duplicate', contextMenu.item)
  }
}
</script>

<style scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #252526;
  user-select: none;
}

.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 8px;
  border-bottom: 1px solid #3c3c3c;
}

.tree-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #999;
  font-weight: 600;
}

.btn-icon {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px;
  border-radius: 3px;
  display: flex;
  align-items: center;
}

.btn-icon:hover {
  background: #3c3c3c;
  color: #fff;
}

.tree-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #ccc;
  position: relative;
}

.tree-item:hover {
  background: #2a2d2e;
}

.tree-item.active {
  background: #37373d;
  color: #fff;
}

.item-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-version {
  font-size: 10px;
  color: #666;
  flex-shrink: 0;
}

.empty-hint {
  padding: 24px 12px;
  font-size: 12px;
  color: #666;
  text-align: center;
  line-height: 1.6;
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  background: #2d2d2d;
  border: 1px solid #454545;
  border-radius: 4px;
  padding: 4px 0;
  min-width: 120px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 1000;
}

.menu-item {
  padding: 6px 16px;
  font-size: 12px;
  color: #ccc;
  cursor: pointer;
}

.menu-item:hover {
  background: #094771;
  color: #fff;
}

.menu-item.danger {
  color: #f48771;
}

.menu-item.danger:hover {
  background: #5a1d1d;
}
</style>
