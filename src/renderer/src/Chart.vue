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

// 从 localStorage 获取数据源设置
function getDataSource() {
  return localStorage.getItem('data-source') || 'binance'
}

// 初始化数据源
function initDataFeed() {
  try {
    const currentDataSource = getDataSource()
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

onMounted(() => {
  initDataFeed()
  
  // 监听 localStorage 变化（用于响应设置页面的数据源切换）
  window.addEventListener('storage', (e) => {
    if (e.key === 'data-source' && e.newValue !== e.oldValue) {
      console.log('[Chart] 检测到数据源变化，重新初始化:', e.newValue)
      initDataFeed()
    }
  })
  
  // 使用自定义事件来监听同窗口内的 localStorage 变化
  // 因为 storage 事件只在其他窗口/标签页触发
  window.addEventListener('dataSourceChanged', (e) => {
    console.log('[Chart] 收到数据源变化事件:', e.detail)
    initDataFeed()
  })
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
