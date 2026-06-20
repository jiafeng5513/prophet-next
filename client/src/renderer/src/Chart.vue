<script setup>
import { ref, onMounted, watch } from 'vue'
import TVChartContainer from '@renderer/components/TVChartContainer.vue'
import BinanceDataFeed from '@renderer/service/dataSource/binance/datafeed'
import OKXDataFeed from '@renderer/service/dataSource/okx/datafeed'
import UnifiedDataFeed from '@renderer/service/dataSource/unified/datafeed'

// 数据源实例
const dataFeed = ref(null)
const errorMessage = ref('')
const dataSource = ref('binance') // 当前使用的数据源
const defaultSymbol = ref('Binance:BTC/USDT') // 默认交易对
const defaultInterval = ref('15') // 默认周期
const chartKey = ref(0) // 用于强制重建 TVChartContainer

// 通过 IPC load-symbol 传入的标的信息
let pendingSymbolInfo = null

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
    // 如果有来自标的浏览器的标的信息，使用统一数据源
    if (pendingSymbolInfo) {
      const info = pendingSymbolInfo
      console.log('[Chart] 从标的浏览器加载标的:', info)

      if (info.market_type === 'crypto') {
        // crypto 仍使用 Binance/OKX 直连
        const currentDataSource = await getDataSource()
        if (currentDataSource === 'okx') {
          dataFeed.value = new OKXDataFeed(undefined)
          defaultSymbol.value = `OKX:${info.symbol}`
          dataSource.value = 'okx'
        } else {
          dataFeed.value = new BinanceDataFeed(undefined)
          // Binance 格式: "Binance:BTC/USDT"
          const formatted = info.symbol.includes('/') ? info.symbol : info.symbol
          defaultSymbol.value = `Binance:${formatted}`
          dataSource.value = 'binance'
        }
      } else {
        // A 股 / ETF 等使用统一 DataFeed
        dataFeed.value = new UnifiedDataFeed({ symbolInfo: info })
        defaultSymbol.value = `${info.exchange}:${info.symbol}`
        defaultInterval.value = '1D' // A 股默认日 K
        dataSource.value = 'unified'
        console.log('[Chart] 统一数据源初始化成功, symbol:', defaultSymbol.value)
      }
      return
    }

    // 默认行为：根据设置创建对应的 crypto 数据源实例
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
  // 监听来自标的浏览器的 load-symbol 消息
  if (window.electronAPI?.onLoadSymbol) {
    window.electronAPI.onLoadSymbol((symbolInfo) => {
      console.log('[Chart] 收到 load-symbol:', symbolInfo)
      pendingSymbolInfo = symbolInfo
      // 清除当前 datafeed, 触发重建
      dataFeed.value = null
      chartKey.value++
      initDataFeed()
    })
  }

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
      :key="chartKey"
      :datafeed="dataFeed"
      :symbol="defaultSymbol"
      :interval="defaultInterval"
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
