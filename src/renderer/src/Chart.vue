<script setup>
import { ref, onMounted } from 'vue'
import TVChartContainer from '@renderer/components/TVChartContainer.vue'
import BinanceDataFeed from '@renderer/service/dataSource/binance/datafeed'

// 创建 binance 数据源实例，添加错误处理
const binanceDataFeed = ref(null)
const errorMessage = ref('')

onMounted(() => {
  try {
    console.log('[Chart] 正在初始化 Binance 数据源...')
    // 传递 undefined 或空对象，让构造函数使用默认配置
    binanceDataFeed.value = new BinanceDataFeed(undefined)
    console.log('[Chart] Binance 数据源初始化成功')
  } catch (error) {
    console.error('[Chart] Binance 数据源初始化失败:', error)
    errorMessage.value = `数据源初始化失败: ${error.message || error}`
  }
})
</script>

<template>
  <div class="app">
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
    <TVChartContainer
      v-else-if="binanceDataFeed"
      :datafeed="binanceDataFeed"
      symbol="Binance:BTC/USDT"
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
