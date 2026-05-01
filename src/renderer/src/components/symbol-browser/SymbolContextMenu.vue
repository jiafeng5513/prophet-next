<template>
  <Teleport to="body">
    <div
      class="context-menu-overlay"
      @click.self="$emit('close')"
      @contextmenu.prevent="$emit('close')"
    >
      <div
        class="context-menu"
        ref="menuRef"
        :style="menuStyle"
      >
        <div class="menu-header">
          <span class="menu-symbol">{{ symbol?.symbol }}</span>
          <span class="menu-name">{{ symbol?.name }}</span>
        </div>
        <div class="menu-divider"></div>
        <div class="menu-item" @click="$emit('open-chart', symbol)">
          <span class="menu-icon">📈</span>
          <span>在图表中打开</span>
        </div>
        <div class="menu-item" @click="$emit('market-analyze', symbol)">
          <span class="menu-icon">🔍</span>
          <span>市场分析</span>
        </div>
        <div class="menu-divider"></div>
        <div class="menu-item" @click="$emit('toggle-watchlist', symbol)">
          <span class="menu-icon">{{ inWatchlist ? '⭐' : '☆' }}</span>
          <span>{{ inWatchlist ? '从自选移除' : '添加到自选' }}</span>
        </div>
        <div class="menu-item" @click="$emit('copy-code', symbol)">
          <span class="menu-icon">📋</span>
          <span>复制代码</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'

const props = defineProps({
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  symbol: { type: Object, default: null },
  inWatchlist: { type: Boolean, default: false }
})

defineEmits(['open-chart', 'market-analyze', 'toggle-watchlist', 'copy-code', 'close'])

const menuRef = ref(null)
const adjustedX = ref(props.x)
const adjustedY = ref(props.y)

const menuStyle = computed(() => ({
  left: adjustedX.value + 'px',
  top: adjustedY.value + 'px'
}))

onMounted(async () => {
  await nextTick()
  if (menuRef.value) {
    const rect = menuRef.value.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight

    if (props.x + rect.width > vw) {
      adjustedX.value = vw - rect.width - 4
    }
    if (props.y + rect.height > vh) {
      adjustedY.value = vh - rect.height - 4
    }
  }
})
</script>

<style scoped>
.context-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.context-menu {
  position: fixed;
  min-width: 180px;
  background: #2d2d2d;
  border: 1px solid #454545;
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  padding: 4px 0;
  z-index: 10000;
}

.menu-header {
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.menu-symbol {
  font-family: 'Consolas', 'Monaco', monospace;
  color: #ddd;
  font-size: 12px;
  font-weight: 600;
}

.menu-name {
  color: #888;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-divider {
  height: 1px;
  background: #404040;
  margin: 4px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.1s;
}

.menu-item:hover {
  background: #094771;
  color: #fff;
}

.menu-icon {
  font-size: 13px;
  width: 18px;
  text-align: center;
}
</style>
