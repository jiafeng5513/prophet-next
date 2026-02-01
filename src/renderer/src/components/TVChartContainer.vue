<script setup>
import { onMounted, ref, onUnmounted } from 'vue'
import { widget } from '@tradingview/trading_platform/charting_library'
import { UDFCompatibleDatafeed } from '@tradingview/trading_platform/datafeeds/udf/src/udf-compatible-datafeed'

function getLanguageFromURL() {
  const regex = new RegExp('[\\?&]lang=([^&#]*)')
  const results = regex.exec(window.location.search)
  return results === null ? null : decodeURIComponent(results[1].replace(/\+/g, ' '))
}

const props = defineProps({
  symbol: {
    default: 'AAPL',
    type: String
  },
  interval: {
    default: 'D',
    type: String
  },
  datafeedUrl: {
    default: 'https://demo_feed.tradingview.com',
    type: String
  },
  datafeed: {
    default: null,
    type: Object
  },
  libraryPath: {
    default: 'tradingview/trading_platform/charting_library/',
    type: String
  },
  chartsStorageUrl: {
    default: 'https://saveload.tradingview.com',
    type: String
  },
  chartsStorageApiVersion: {
    default: '1.1',
    type: String
  },
  clientId: {
    default: 'tradingview.com',
    type: String
  },
  userId: {
    default: 'public_user_id',
    type: String
  },
  fullscreen: {
    default: false,
    type: Boolean
  },
  autosize: {
    default: true,
    type: Boolean
  },
  studiesOverrides: {
    type: Object
  }
})

const chartContainer = ref()
let chartWidget

onMounted(() => {
  try {
    console.log('[TVChartContainer] 开始初始化图表组件')
    console.log('[TVChartContainer] datafeed:', props.datafeed)
    console.log('[TVChartContainer] symbol:', props.symbol)
    console.log('[TVChartContainer] interval:', props.interval)

    // 如果提供了 datafeed 实例，使用它；否则使用 datafeedUrl 创建 UDFCompatibleDatafeed
    const datafeedInstance = props.datafeed || new UDFCompatibleDatafeed(props.datafeedUrl)
    console.log('[TVChartContainer] 数据源实例:', datafeedInstance)

    if (!chartContainer.value) {
      console.error('[TVChartContainer] 容器元素未找到')
      return
    }

    const widgetOptions = {
      symbol: props.symbol,
      datafeed: datafeedInstance,
      interval: props.interval,
      container: chartContainer.value,
      library_path: props.libraryPath,

      locale: getLanguageFromURL() || 'en',
      disabled_features: [
        'use_localstorage_for_settings',
        'open_account_manager',
        'show_object_tree'
      ],
      enabled_features: ['study_templates', 'hide_object_tree_and_price_scale_exchange_label'],
      charts_storage_url: props.chartsStorageUrl,
      charts_storage_api_version: props.chartsStorageApiVersion,
      client_id: props.clientId,
      user_id: props.userId,
      fullscreen: props.fullscreen,
      autosize: props.autosize,
      studies_overrides: props.studiesOverrides,
      theme: 'Dark',
      timezone: 'Asia/Shanghai'
    }
    console.log('[TVChartContainer] 创建图表组件，选项:', widgetOptions)
    chartWidget = new widget(widgetOptions)
    console.log('[TVChartContainer] 图表组件创建成功')
  } catch (error) {
    console.error('[TVChartContainer] 初始化失败:', error)
    throw error
  }

  chartWidget.onChartReady(() => {
    // 辅助函数：更新标题并通知父窗口（浏览器模式）
    const updateTitle = (title) => {
      document.title = title
      console.log('[TVChartContainer] Updated page title to:', title)
      console.log('[TVChartContainer] window.parent:', window.parent)
      console.log('[TVChartContainer] window.parent !== window:', window.parent !== window)

      // 在浏览器模式下，通过 postMessage 通知父窗口标题变化
      if (window.parent && window.parent !== window) {
        try {
          const message = {
            type: 'iframe-title-updated',
            title: title
          }
          console.log('[TVChartContainer] Sending message to parent:', message)
          window.parent.postMessage(message, '*') // 在开发环境中使用 '*'，生产环境应指定具体 origin
          console.log('[TVChartContainer] Message sent successfully to parent:', title)
        } catch (error) {
          console.error('[TVChartContainer] Failed to send title update:', error)
        }
      } else {
        console.log('[TVChartContainer] Not in iframe, skipping postMessage')
      }
    }

    // 设置初始标题（只显示 symbol，不包含 "- Chart" 后缀）
    const initialSymbol = props.symbol.replace(/^Binance:/, '') || props.symbol
    // 移除可能的 "/" 分隔符，转换为 "BTCUSDT" 格式
    const initialSymbolFormatted = initialSymbol.replace(/\//g, '')
    updateTitle(initialSymbolFormatted)

    // 监听 symbol 变化，同步更新页面标题
    // onSymbolChanged 需要通过 activeChart() 获取
    chartWidget
      .activeChart()
      .onSymbolChanged()
      .subscribe(null, () => {
        try {
          // 获取当前 symbol
          const symbolInfo = chartWidget.activeChart().symbol()
          console.log(
            '[TVChartContainer] Symbol info type:',
            typeof symbolInfo,
            'value:',
            symbolInfo
          )

          let symbolName = ''

          // symbol() 可能返回字符串或对象
          if (typeof symbolInfo === 'string') {
            // 如果是字符串，直接使用
            symbolName = symbolInfo
          } else if (symbolInfo && typeof symbolInfo === 'object') {
            // 如果是对象，尝试从不同属性获取
            symbolName = symbolInfo.name || symbolInfo.ticker || symbolInfo.symbol || ''
          }

          console.log('[TVChartContainer] Extracted symbol name:', symbolName)

          if (symbolName && symbolName.trim()) {
            // 格式化 symbol 名称，移除 "Binance:" 或 "BINANCE:" 前缀（如果有，不区分大小写）
            let displayName = symbolName.replace(/^Binance:/i, '').trim()
            // 移除 "/" 分隔符，转换为 "BTCUSDT" 格式
            displayName = displayName.replace(/\//g, '').trim()

            if (displayName) {
              updateTitle(displayName)
            } else {
              console.warn(
                '[TVChartContainer] Display name is empty after formatting, symbolName:',
                symbolName
              )
            }
          } else {
            console.warn('[TVChartContainer] Symbol name is empty, symbolInfo:', symbolInfo)
          }
        } catch (error) {
          console.error('[TVChartContainer] Error getting symbol info:', error)
        }
      })

    chartWidget.headerReady().then(() => {
      const button = chartWidget.createButton()

      button.setAttribute('title', 'Click to show a notification popup')
      button.classList.add('apply-common-tooltip')

      button.addEventListener('click', () =>
        chartWidget.showNoticeDialog({
          title: 'Notification',
          body: 'TradingView Charting Library API works correctly',
          callback: () => {
            console.log('Noticed!')
          }
        })
      )

      button.innerHTML = 'Check API'
    })
  })
})

onUnmounted(() => {
  if (chartWidget !== null) {
    chartWidget.remove()
    chartWidget = null
  }
})
</script>

<template>
  <div ref="chartContainer" class="TVChartContainer" />
</template>

<style scoped>
.TVChartContainer {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>
