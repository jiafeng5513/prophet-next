<template>
  <div class="compare-analysis" v-if="items.length > 1">
    <div class="compare-header">
      <span class="compare-title">📊 对比分析</span>
      <button class="compare-close" @click="$emit('close')">✕</button>
    </div>
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th>维度</th>
            <th v-for="item in items" :key="item.stockCode">{{ item.stockCode }}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>信号</td>
            <td v-for="item in items" :key="'sig-' + item.stockCode">
              <span class="signal-tag" :class="'signal--' + item.dashboard.signal">{{ item.dashboard.signal }}</span>
            </td>
          </tr>
          <tr>
            <td>置信度</td>
            <td v-for="item in items" :key="'conf-' + item.stockCode">
              {{ ((item.dashboard.confidence || 0) * 100).toFixed(0) }}%
            </td>
          </tr>
          <tr>
            <td>趋势</td>
            <td v-for="item in items" :key="'trend-' + item.stockCode">
              {{ item.dashboard.market_context?.trend || '-' }}
            </td>
          </tr>
          <tr>
            <td>情绪</td>
            <td v-for="item in items" :key="'sent-' + item.stockCode">
              {{ item.dashboard.market_context?.sentiment || '-' }}
            </td>
          </tr>
          <tr>
            <td>辩论裁决</td>
            <td v-for="item in items" :key="'deb-' + item.stockCode">
              {{ item.dashboard.debate_summary?.manager_verdict || '-' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DashboardData } from '../../service/chatService'

export interface CompareItem {
  stockCode: string
  stockName?: string
  dashboard: DashboardData
}

defineProps<{
  items: CompareItem[]
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.compare-analysis {
  background: #1e2a36;
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
}

.compare-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.compare-title {
  font-size: 13px;
  font-weight: 600;
  color: #8bb8d4;
}

.compare-close {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 14px;
}

.compare-table-wrap {
  overflow-x: auto;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.compare-table th,
.compare-table td {
  padding: 6px 10px;
  border: 1px solid #2a3f52;
  text-align: center;
  color: #ccc;
}

.compare-table th {
  background: #253d52;
  color: #b8d4e8;
  font-weight: 600;
}

.compare-table td:first-child {
  text-align: left;
  color: #aaa;
  font-weight: 500;
}

.signal-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
}

.signal--buy, .signal--买入 { background: #1b4332; color: #52c41a; }
.signal--sell, .signal--卖出 { background: #3b1325; color: #ff4d4f; }
.signal--hold, .signal--持有 { background: #2a2000; color: #faad14; }
</style>
