<script setup>
import { ref, onMounted, watch } from 'vue'
import TVChartContainer from '@renderer/components/TVChartContainer.vue'
import BinanceDataFeed from '@renderer/service/dataSource/binance/datafeed'
import OKXDataFeed from '@renderer/service/dataSource/okx/datafeed'

// 数据源实例
const dataFeed = ref(null)
const errorMessage = ref('')
const dataSource = ref('binance') // 当前使用的数据源
const defaultSymbol = ref('Binance:BTC/USDT') // 默认交易对

// 从主进程获取数据源设置（解决跨 partition localStorage 隔离问题）
async function getDataSource() {
  if (window.electronAPI && window.electronAPI.getDataSource) {
    return await window.electronAPI.getDataSource()
  }
  // 浏览器模式回退到 localStorage
  return localStorage.getItem('data-source') || 'binance'
}

// 初始化数据源
async function initDataFeed() {
  try {
    const currentDataSource = await getDataSource()
    console.log('[Chart] 正在初始化数据源:', currentDataSource)
    
    // 根据设置创建对应的数据源实例
    if (currentDataSource === 'okx') {
      dataFeed.value = new OKXDataFeed(undefined)
      defaultSymbol.value = 'OKX:BTC/USDT'
      dataSource.value = 'okx'
      console.log('[Chart] OKX 数据源初始化成功')
    } else {
      dataFeed.value = new BinanceDataFeed(undefined)
      defaultSymbol.value = 'Binance:BTC/USDT'
      dataSource.value = 'binance'
      console.log('[Chart] Binance 数据源初始化成功')
    }
  } catch (error) {
    console.error('[Chart] 数据源初始化失败:', error)
    errorMessage.value = `数据源初始化失败: ${error.message || error}`
  }
}

onMounted(async () => {
  await initDataFeed()
})
</script>

<template>
  <div class="app">
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
    <TVChartContainer
      v-else-if="dataFeed"
      :datafeed="dataFeed"
      :symbol="defaultSymbol"
      interval="15"
      :fullscreen="true"
      class="chart-container"
    />
    <div v-else class="loading-message">
      正在加载图表...
    </div>
  </div>
</template>

<style scoped>
.app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.error-message {
  color: #ff4444;
  padding: 20px;
  background-color: #ffe6e6;
  border: 1px solid #ff4444;
  border-radius: 4px;
  margin: 20px;
}

.loading-message {
  color: #666;
  padding: 20px;
  font-size: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.app_header {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
  background-color: #222;
  color: #fff;
  height: 60px;
  max-height: 60px;
  padding: 10px;
}

.app_title {
  display: block;
  font-size: 1.25em;
}
</style>
