<template>
  <div class="dashboard-result">
    <div class="dashboard-result__header">
      <span class="dashboard-title">分析结论</span>
    </div>

    <div class="dashboard-result__body">
      <!-- 信号 + 置信度 -->
      <div class="dashboard-signal-row" v-if="dashboard.signal || dashboard.confidence != null">
        <div v-if="dashboard.signal" class="signal-badge" :class="`signal-badge--${dashboard.signal}`">
          {{ signalLabel(dashboard.signal) }}
        </div>
        <div v-if="dashboard.confidence != null" class="confidence-bar">
          <div class="confidence-fill" :style="{ width: (dashboard.confidence * 100) + '%' }"></div>
          <span class="confidence-text">{{ (dashboard.confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- 摘要 -->
      <div v-if="dashboard.summary" class="dashboard-summary">
        {{ dashboard.summary }}
      </div>

      <!-- 操作按钮 -->
      <div class="dashboard-actions">
        <button class="action-btn" @click="$emit('annotate')" title="在K线图上标注信号">
          📍 在K线标注
        </button>
        <button class="action-btn" @click="$emit('chat')" title="在侧边栏继续追问">
          💬 继续对话
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DashboardData } from '../../service/chatService'

defineProps<{
  dashboard: DashboardData
}>()

defineEmits<{
  'annotate': []
  'chat': []
}>()

function signalLabel(signal: string) {
  const map: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有', alert: '警戒' }
  return map[signal] || signal
}
</script>

<style scoped>
.dashboard-result {
  background: #1a2634;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 12px;
}

.dashboard-result__header {
  padding: 10px 16px;
  border-bottom: 1px solid #2a3a4a;
}

.dashboard-title {
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
}

.dashboard-result__body {
  padding: 12px 16px;
}

.dashboard-signal-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.signal-badge {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
}

.signal-badge--buy { background: #1b4332; color: #52c41a; }
.signal-badge--sell { background: #3b1325; color: #ff4d4f; }
.signal-badge--hold { background: #2a2000; color: #faad14; }
.signal-badge--alert { background: #2a1b00; color: #ffa940; }

.confidence-bar {
  flex: 1;
  height: 20px;
  background: #252525;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #0e639c, #4fc1ff);
  border-radius: 10px;
  transition: width 0.5s ease;
}

.confidence-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  color: #fff;
  font-weight: 500;
}

.dashboard-summary {
  font-size: 13px;
  color: #bbb;
  line-height: 1.5;
  margin-bottom: 12px;
}

.dashboard-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: #253d52;
  border: 1px solid #3a5f7a;
  border-radius: 6px;
  color: #b8d4e8;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.action-btn:hover {
  background: #2d4f6a;
  border-color: #4a7fa0;
}
</style>
