<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import KLineChartContainer from '@renderer/components/KLineChartContainer.vue'
import BinanceDataLoader from '@renderer/service/dataSource/binance/dataLoader'
import OKXDataLoader from '@renderer/service/dataSource/okx/dataLoader'

// 数据源实例
const dataLoader = ref(null)
const errorMessage = ref('')
const dataSource = ref('binance')
const defaultSymbol = ref('Binance:BTC/USDT')
const defaultExchange = ref('Binance')

// 当前 loader 实例引用（用于销毁）
let currentLoader = null

// 从主进程获取数据源设置（解决跨 partition localStorage 隔离问题）
async function getDataSource() {
  if (window.electronAPI && window.electronAPI.getDataSource) {
    return await window.electronAPI.getDataSource()
  }
  // 浏览器模式回退到 localStorage
  return localStorage.getItem('data-source') || 'binance'
}

// 初始化数据源
async function initDataLoader() {
  try {
    const currentDataSource = await getDataSource()
    console.log('[Chart] 正在初始化数据源:', currentDataSource)
    
    if (currentDataSource === 'okx') {
      currentLoader = new OKXDataLoader()
      dataLoader.value = currentLoader
      defaultSymbol.value = 'OKX:BTC/USDT'
      defaultExchange.value = 'OKX'
      dataSource.value = 'okx'
      console.log('[Chart] OKX 数据源初始化成功')
    } else {
      currentLoader = new BinanceDataLoader()
      dataLoader.value = currentLoader
      defaultSymbol.value = 'Binance:BTC/USDT'
      defaultExchange.value = 'Binance'
      dataSource.value = 'binance'
      console.log('[Chart] Binance 数据源初始化成功')
    }
  } catch (error) {
    console.error('[Chart] 数据源初始化失败:', error)
    errorMessage.value = `数据源初始化失败: ${error.message || error}`
  }
}

onMounted(async () => {
  await initDataLoader()
})

onUnmounted(() => {
  if (currentLoader && currentLoader.destroy) {
    currentLoader.destroy()
    currentLoader = null
  }
})
</script>

<template>
  <div class="app">
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
    <KLineChartContainer
      v-else-if="dataLoader"
      :dataLoader="dataLoader"
      :symbol="defaultSymbol"
      :exchange="defaultExchange"
      interval="15"
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
