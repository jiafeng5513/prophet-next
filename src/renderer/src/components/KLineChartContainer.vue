<script setup>
import { onMounted, ref, reactive, computed, onUnmounted, watch, nextTick } from 'vue'
import { init, dispose, ActionType, TooltipIconPosition } from 'klinecharts'
import { registerProOverlays } from '@renderer/utils/overlayExtensions'

// Register custom overlay extensions from klinecharts-pro
registerProOverlays()

const props = defineProps({
  symbol: { default: 'BTC/USDT', type: String },
  exchange: { default: 'Binance', type: String },
  interval: { default: '15', type: String },
  dataLoader: { default: null, type: Object }
})

const chartContainer = ref()
let chartInstance = null

const currentInterval = ref(props.interval)
const drawingBarVisible = ref(true)
const isFullScreen = ref(false)
const loadingVisible = ref(false)

// ===== 周期选项 (Pro 风格: multiplier + timespan) =====
const periods = [
  { label: '1m', value: '1' },
  { label: '5m', value: '5' },
  { label: '15m', value: '15' },
  { label: '1H', value: '60' },
  { label: '4H', value: '240' },
  { label: '1D', value: '1D' },
  { label: '1W', value: '1W' },
  { label: '1M', value: '1M' }
]

// ===== 指标列表 =====
const mainIndicatorList = ['MA', 'EMA', 'BOLL', 'SAR', 'BBI', 'SMA']
const subIndicatorList = ['VOL', 'MACD', 'KDJ', 'RSI', 'DMI', 'CR', 'WR', 'OBV', 'CCI', 'BIAS', 'MTM', 'ROC', 'TRIX', 'AVP', 'AO', 'BRAR', 'DMA', 'EMV', 'PSY', 'PVT', 'VR']
const activeMainIndicators = reactive(new Set())
const activeSubIndicators = reactive(new Map())
const indicatorModalVisible = ref(false)

// ===== 指标设置弹窗 =====
const indicatorSettingModal = reactive({
  visible: false,
  indicatorName: '',
  paneId: '',
  calcParams: []
})

// ===== 指标参数配置 (from KLineChart Pro) =====
const indicatorParamConfig = {
  MA: [
    { paramNameKey: 'MA1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'MA2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'MA3', precision: 0, min: 1, styleKey: 'lines[2]' },
    { paramNameKey: 'MA4', precision: 0, min: 1, styleKey: 'lines[3]' },
    { paramNameKey: 'MA5', precision: 0, min: 1, styleKey: 'lines[4]' }
  ],
  EMA: [
    { paramNameKey: 'EMA1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'EMA2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'EMA3', precision: 0, min: 1, styleKey: 'lines[2]' },
    { paramNameKey: 'EMA4', precision: 0, min: 1, styleKey: 'lines[3]' },
    { paramNameKey: 'EMA5', precision: 0, min: 1, styleKey: 'lines[4]' }
  ],
  SMA: [
    { paramNameKey: 'SMA1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'SMA2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'SMA3', precision: 0, min: 1, styleKey: 'lines[2]' },
    { paramNameKey: 'SMA4', precision: 0, min: 1, styleKey: 'lines[3]' },
    { paramNameKey: 'SMA5', precision: 0, min: 1, styleKey: 'lines[4]' }
  ],
  BOLL: [
    { paramNameKey: '周期', precision: 0, min: 1 },
    { paramNameKey: '标准差', precision: 0, min: 1 }
  ],
  SAR: [
    { paramNameKey: '起始值', precision: 0, min: 1 },
    { paramNameKey: '增量', precision: 0, min: 1 },
    { paramNameKey: '最大值', precision: 0, min: 1 }
  ],
  BBI: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 },
    { paramNameKey: '周期3', precision: 0, min: 1 },
    { paramNameKey: '周期4', precision: 0, min: 1 }
  ],
  VOL: [
    { paramNameKey: 'MA1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'MA2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'MA3', precision: 0, min: 1, styleKey: 'lines[2]' },
    { paramNameKey: 'MA4', precision: 0, min: 1, styleKey: 'lines[3]' },
    { paramNameKey: 'MA5', precision: 0, min: 1, styleKey: 'lines[4]' }
  ],
  MACD: [
    { paramNameKey: '快周期', precision: 0, min: 1 },
    { paramNameKey: '慢周期', precision: 0, min: 1 },
    { paramNameKey: '信号周期', precision: 0, min: 1 }
  ],
  KDJ: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 },
    { paramNameKey: '周期3', precision: 0, min: 1 }
  ],
  RSI: [
    { paramNameKey: 'RSI1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'RSI2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'RSI3', precision: 0, min: 1, styleKey: 'lines[2]' },
    { paramNameKey: 'RSI4', precision: 0, min: 1, styleKey: 'lines[3]' },
    { paramNameKey: 'RSI5', precision: 0, min: 1, styleKey: 'lines[4]' }
  ],
  DMI: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  CR: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 },
    { paramNameKey: '周期3', precision: 0, min: 1 },
    { paramNameKey: '周期4', precision: 0, min: 1 },
    { paramNameKey: '周期5', precision: 0, min: 1 }
  ],
  WR: [
    { paramNameKey: 'WR1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'WR2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'WR3', precision: 0, min: 1, styleKey: 'lines[2]' }
  ],
  OBV: [
    { paramNameKey: '周期', precision: 0, min: 1 }
  ],
  CCI: [
    { paramNameKey: '周期', precision: 0, min: 1 }
  ],
  BIAS: [
    { paramNameKey: 'BIAS1', precision: 0, min: 1, styleKey: 'lines[0]' },
    { paramNameKey: 'BIAS2', precision: 0, min: 1, styleKey: 'lines[1]' },
    { paramNameKey: 'BIAS3', precision: 0, min: 1, styleKey: 'lines[2]' }
  ],
  MTM: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  ROC: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  TRIX: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  AVP: [],
  AO: [],
  BRAR: [
    { paramNameKey: '周期', precision: 0, min: 1 }
  ],
  DMA: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 },
    { paramNameKey: '周期3', precision: 0, min: 1 }
  ],
  EMV: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  PSY: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ],
  PVT: [],
  VR: [
    { paramNameKey: '周期1', precision: 0, min: 1 },
    { paramNameKey: '周期2', precision: 0, min: 1 }
  ]
}

// ===== 画线工具 (Pro 风格: 5 组 + 磁吸 + 工具按钮) =====
const DRAWING_GROUP_ID = 'drawing_tools'

const singleLineTools = [
  { key: 'horizontalStraightLine', text: '水平直线' },
  { key: 'horizontalRayLine', text: '水平射线' },
  { key: 'horizontalSegment', text: '水平线段' },
  { key: 'verticalStraightLine', text: '垂直直线' },
  { key: 'verticalRayLine', text: '垂直射线' },
  { key: 'verticalSegment', text: '垂直线段' },
  { key: 'straightLine', text: '直线' },
  { key: 'rayLine', text: '射线' },
  { key: 'segment', text: '线段' },
  { key: 'arrow', text: '箭头' },
  { key: 'priceLine', text: '价格线' }
]

const moreLineTools = [
  { key: 'priceChannelLine', text: '价格通道线' },
  { key: 'parallelStraightLine', text: '平行直线' }
]

const polygonTools = [
  { key: 'circle', text: '圆' },
  { key: 'rect', text: '矩形' },
  { key: 'parallelogram', text: '平行四边形' },
  { key: 'triangle', text: '三角形' }
]

const fibonacciTools = [
  { key: 'fibonacciLine', text: '斐波那契回撤' },
  { key: 'fibonacciSegment', text: '斐波那契线段' },
  { key: 'fibonacciCircle', text: '斐波那契圆' },
  { key: 'fibonacciSpiral', text: '斐波那契螺旋线' },
  { key: 'fibonacciSpeedResistanceFan', text: '斐波那契速度阻力扇' },
  { key: 'fibonacciExtension', text: '斐波那契扩展' },
  { key: 'gannBox', text: '江恩箱' }
]

const waveTools = [
  { key: 'xabcd', text: 'XABCD 模式' },
  { key: 'abcd', text: 'ABCD 模式' },
  { key: 'threeWaves', text: '三浪' },
  { key: 'fiveWaves', text: '五浪' },
  { key: 'eightWaves', text: '八浪' },
  { key: 'anyWaves', text: '任意浪' }
]

const singleLineIcon = ref('horizontalStraightLine')
const moreLineIcon = ref('priceChannelLine')
const polygonIcon = ref('circle')
const fibonacciIcon = ref('fibonacciLine')
const waveIcon = ref('xabcd')

const overlayGroups = computed(() => [
  { key: 'singleLine', icon: singleLineIcon.value, list: singleLineTools, setter: v => { singleLineIcon.value = v } },
  { key: 'moreLine', icon: moreLineIcon.value, list: moreLineTools, setter: v => { moreLineIcon.value = v } },
  { key: 'polygon', icon: polygonIcon.value, list: polygonTools, setter: v => { polygonIcon.value = v } },
  { key: 'fibonacci', icon: fibonacciIcon.value, list: fibonacciTools, setter: v => { fibonacciIcon.value = v } },
  { key: 'wave', icon: waveIcon.value, list: waveTools, setter: v => { waveIcon.value = v } }
])

const magnetTools = [
  { key: 'weak_magnet', text: '弱磁吸' },
  { key: 'strong_magnet', text: '强磁吸' }
]

const popoverKey = ref('')
const drawingLock = ref(false)
const drawingVisible = ref(true)
const drawingMode = ref('normal')
const magnetIcon = ref('weak_magnet')

const displaySymbol = computed(() => {
  let name = props.symbol
  const prefixPattern = new RegExp(`^${props.exchange}:`, 'i')
  name = name.replace(prefixPattern, '').replace(/\//g, '')
  return name.trim()
})

// ===== 暗色主题 (匹配 Pro 配色) =====
const darkThemeStyles = {
  grid: {
    show: true,
    horizontal: { color: 'rgba(255, 255, 255, 0.04)' },
    vertical: { color: 'rgba(255, 255, 255, 0.04)' }
  },
  candle: {
    bar: {
      upColor: '#26A69A', downColor: '#EF5350', noChangeColor: '#888888',
      upBorderColor: '#26A69A', downBorderColor: '#EF5350', noChangeBorderColor: '#888888',
      upWickColor: '#26A69A', downWickColor: '#EF5350', noChangeWickColor: '#888888'
    },
    tooltip: { text: { color: '#D1D4DC' } }
  },
  indicator: {
    tooltip: {
      text: { color: '#D1D4DC' },
      icons: [
        {
          id: 'visible',
          position: TooltipIconPosition.Middle,
          marginLeft: 8, marginTop: 5, marginRight: 0, marginBottom: 0,
          paddingLeft: 2, paddingTop: 2, paddingRight: 2, paddingBottom: 2,
          icon: '\uD83D\uDC41', fontFamily: 'Arial', size: 18,
          color: '#929AA5', activeColor: '#D1D4DC',
          backgroundColor: 'transparent', activeBackgroundColor: 'rgba(22, 119, 255, 0.15)'
        },
        {
          id: 'invisible',
          position: TooltipIconPosition.Middle,
          marginLeft: 8, marginTop: 5, marginRight: 0, marginBottom: 0,
          paddingLeft: 2, paddingTop: 2, paddingRight: 2, paddingBottom: 2,
          icon: '\uD83D\uDC41', fontFamily: 'Arial', size: 18,
          color: '#555555', activeColor: '#777777',
          backgroundColor: 'transparent', activeBackgroundColor: 'rgba(22, 119, 255, 0.15)'
        },
        {
          id: 'setting',
          position: TooltipIconPosition.Middle,
          marginLeft: 6, marginTop: 5, marginRight: 0, marginBottom: 0,
          paddingLeft: 2, paddingTop: 2, paddingRight: 2, paddingBottom: 2,
          icon: '\u2699', fontFamily: 'Arial', size: 18,
          color: '#929AA5', activeColor: '#D1D4DC',
          backgroundColor: 'transparent', activeBackgroundColor: 'rgba(22, 119, 255, 0.15)'
        },
        {
          id: 'close',
          position: TooltipIconPosition.Middle,
          marginLeft: 6, marginTop: 5, marginRight: 0, marginBottom: 0,
          paddingLeft: 2, paddingTop: 2, paddingRight: 2, paddingBottom: 2,
          icon: '\u2716', fontFamily: 'Arial', size: 16,
          color: '#929AA5', activeColor: '#D1D4DC',
          backgroundColor: 'transparent', activeBackgroundColor: 'rgba(22, 119, 255, 0.15)'
        }
      ]
    }
  },
  xAxis: {
    axisLine: { color: '#292929' }, tickLine: { color: '#292929' },
    tickText: { color: '#929AA5' }
  },
  yAxis: {
    axisLine: { color: '#292929' }, tickLine: { color: '#292929' },
    tickText: { color: '#929AA5' }
  },
  separator: { color: '#292929' },
  crosshair: {
    horizontal: { line: { color: '#555' }, text: { color: '#D1D4DC', backgroundColor: '#373B44' } },
    vertical: { line: { color: '#555' }, text: { color: '#D1D4DC', backgroundColor: '#373B44' } }
  }
}

// ===== 标题 =====
function updateTitle(title) {
  document.title = title
  if (window.parent && window.parent !== window) {
    try { window.parent.postMessage({ type: 'iframe-title-updated', title }, '*') } catch (e) { /* ignore */ }
  }
}

// ===== 周期切换 =====
function switchPeriod(period) {
  if (currentInterval.value === period) return
  currentInterval.value = period
  reloadData()
}

// ===== 指标操作 =====
function createIndicatorWithTooltip(indicatorName, isStack, paneOptions) {
  if (!chartInstance) return null
  const opts = indicatorName === 'VOL'
    ? { gap: { bottom: 2 }, ...paneOptions }
    : paneOptions
  return chartInstance.createIndicator({
    name: indicatorName,
    createTooltipDataSource: ({ indicator, defaultStyles }) => {
      const icons = []
      if (indicator.visible) {
        icons.push(defaultStyles.tooltip.icons[0]) // visible (eye)
        icons.push(defaultStyles.tooltip.icons[2]) // setting (gear)
        icons.push(defaultStyles.tooltip.icons[3]) // close (x)
      } else {
        icons.push(defaultStyles.tooltip.icons[1]) // invisible (dimmed eye)
        icons.push(defaultStyles.tooltip.icons[2]) // setting (gear)
        icons.push(defaultStyles.tooltip.icons[3]) // close (x)
      }
      return { icons }
    }
  }, isStack, opts) ?? null
}

function toggleMainIndicator(name) {
  if (!chartInstance) return
  if (activeMainIndicators.has(name)) {
    chartInstance.removeIndicator('candle_pane', name)
    activeMainIndicators.delete(name)
  } else {
    createIndicatorWithTooltip(name, true, { id: 'candle_pane' })
    activeMainIndicators.add(name)
  }
}

function toggleSubIndicator(name) {
  if (!chartInstance) return
  if (activeSubIndicators.has(name)) {
    chartInstance.removeIndicator(activeSubIndicators.get(name), name)
    activeSubIndicators.delete(name)
  } else {
    const paneId = createIndicatorWithTooltip(name, true)
    if (paneId) activeSubIndicators.set(name, paneId)
  }
}

function openIndicatorSetting(indicatorName, paneId) {
  if (!chartInstance) return
  const indicator = chartInstance.getIndicatorByPaneId(paneId, indicatorName)
  if (!indicator) return
  indicatorSettingModal.visible = true
  indicatorSettingModal.indicatorName = indicatorName
  indicatorSettingModal.paneId = paneId
  indicatorSettingModal.calcParams = [...indicator.calcParams]
}

function confirmIndicatorSetting() {
  if (!chartInstance) return
  const params = indicatorSettingModal.calcParams.map(v => Number(v))
  chartInstance.overrideIndicator(
    { name: indicatorSettingModal.indicatorName, calcParams: params },
    indicatorSettingModal.paneId
  )
  indicatorSettingModal.visible = false
}

function closeIndicatorSetting() {
  indicatorSettingModal.visible = false
}

// ===== 画线操作 =====
function onDrawingItemClick(overlayName) {
  if (!chartInstance) return
  chartInstance.createOverlay({
    groupId: DRAWING_GROUP_ID,
    name: overlayName,
    visible: drawingVisible.value,
    lock: drawingLock.value,
    mode: drawingMode.value
  })
}

function selectDrawingTool(group, tool) {
  group.setter(tool.key)
  onDrawingItemClick(tool.key)
  popoverKey.value = ''
}

function togglePopover(key) {
  popoverKey.value = popoverKey.value === key ? '' : key
}

function onOverlayLockChange() {
  drawingLock.value = !drawingLock.value
  if (chartInstance) chartInstance.overrideOverlay({ lock: drawingLock.value })
}

function onOverlayVisibleChange() {
  drawingVisible.value = !drawingVisible.value
  if (chartInstance) chartInstance.overrideOverlay({ visible: drawingVisible.value })
}

function onMagnetModeClick() {
  let currentMode = magnetIcon.value
  if (drawingMode.value !== 'normal') {
    currentMode = 'normal'
  }
  drawingMode.value = currentMode
  if (chartInstance) chartInstance.overrideOverlay({ mode: currentMode })
}

function selectMagnetMode(mode) {
  magnetIcon.value = mode.key
  drawingMode.value = mode.key
  if (chartInstance) chartInstance.overrideOverlay({ mode: mode.key })
  popoverKey.value = ''
}

function removeAllOverlays() {
  if (chartInstance) chartInstance.removeOverlay({ groupId: DRAWING_GROUP_ID })
}

// ===== 画线栏显隐 =====
function toggleDrawingBar() {
  drawingBarVisible.value = !drawingBarVisible.value
  nextTick(() => { chartInstance?.resize() })
}

// ===== 截图 =====
function takeScreenshot() {
  if (!chartInstance) return
  const url = chartInstance.getConvertPictureUrl(true, 'jpeg', '#151517')
  const a = document.createElement('a')
  a.href = url
  a.download = `${displaySymbol.value}_${currentInterval.value}.jpg`
  a.click()
}

// ===== 全屏 =====
function toggleFullScreen() {
  const el = chartContainer.value?.parentElement?.parentElement
  if (!el) return
  if (!isFullScreen.value) {
    const enter = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen
    if (enter) enter.call(el)
  } else {
    const exit = document.exitFullscreen || document.msExitFullscreen || document.mozCancelFullScreen || document.webkitExitFullscreen
    if (exit) exit.call(document)
  }
}

function onFullScreenChange() { isFullScreen.value = !isFullScreen.value }

// ===== 数据加载 =====
onMounted(() => {
  if (!chartContainer.value) return

  chartInstance = init(chartContainer.value, {
    locale: 'zh-CN',
    timezone: 'Asia/Shanghai',
    styles: darkThemeStyles
  })
  if (!chartInstance) return

  const volPaneId = createIndicatorWithTooltip('VOL', true)
  if (volPaneId) activeSubIndicators.set('VOL', volPaneId)

  // 订阅指标 tooltip 图标点击事件
  chartInstance.subscribeAction(ActionType.OnTooltipIconClick, (data) => {
    if (!data.indicatorName) return
    switch (data.iconId) {
      case 'visible':
        chartInstance.overrideIndicator({ name: data.indicatorName, visible: false }, data.paneId)
        break
      case 'invisible':
        chartInstance.overrideIndicator({ name: data.indicatorName, visible: true }, data.paneId)
        break
      case 'setting':
        openIndicatorSetting(data.indicatorName, data.paneId)
        break
      case 'close':
        if (data.paneId === 'candle_pane') {
          chartInstance.removeIndicator('candle_pane', data.indicatorName)
          activeMainIndicators.delete(data.indicatorName)
        } else {
          chartInstance.removeIndicator(data.paneId, data.indicatorName)
          activeSubIndicators.delete(data.indicatorName)
        }
        break
    }
  })

  updateTitle(displaySymbol.value)
  if (props.dataLoader) setupDataLoader(props.dataLoader)

  document.addEventListener('fullscreenchange', onFullScreenChange)
  document.addEventListener('webkitfullscreenchange', onFullScreenChange)
})

async function setupDataLoader(loader) {
  if (!chartInstance || !loader) return
  loadingVisible.value = true

  try {
    const bars = await loader.getBars({
      symbol: props.symbol, exchange: props.exchange,
      interval: currentInterval.value, type: 'init'
    })
    chartInstance.applyNewData(bars, bars.length > 0)
  } catch (error) {
    console.error('[KLineChart] 初始数据加载失败:', error)
    chartInstance.applyNewData([], false)
  }

  chartInstance.setLoadDataCallback(({ type, data, callback }) => {
    if (type === 'forward') {
      loader.getBars({
        symbol: props.symbol, exchange: props.exchange,
        interval: currentInterval.value, type: 'forward', timestamp: data?.timestamp
      }).then(bars => callback(bars, bars.length > 0))
        .catch(() => callback([], false))
    }
  })

  if (loader.subscribe) {
    loader.subscribe({
      symbol: props.symbol, exchange: props.exchange,
      interval: currentInterval.value,
      callback: bar => { if (chartInstance) chartInstance.updateData(bar) }
    })
  }

  loadingVisible.value = false
}

async function reloadData() {
  if (!chartInstance || !props.dataLoader) return
  if (props.dataLoader.unsubscribe) props.dataLoader.unsubscribe()
  chartInstance.clearData()
  await setupDataLoader(props.dataLoader)
}

watch(() => props.dataLoader, newLoader => {
  if (newLoader && chartInstance) { chartInstance.clearData(); setupDataLoader(newLoader) }
})

watch(() => props.symbol, newSymbol => {
  if (chartInstance && props.dataLoader) { updateTitle(displaySymbol.value); reloadData() }
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullScreenChange)
  document.removeEventListener('webkitfullscreenchange', onFullScreenChange)
  if (props.dataLoader?.unsubscribe) props.dataLoader.unsubscribe()
  if (chartInstance) { dispose(chartInstance); chartInstance = null }
})
</script>

<template>
  <!-- SVG Icon Sprite Sheet (hidden) -->
  <svg xmlns="http://www.w3.org/2000/svg" style="display:none">
    <defs>
      <!-- === 直线工具 === -->
      <symbol id="icon-horizontalStraightLine" viewBox="0 0 22 22">
        <line x1="2" y1="11" x2="20" y2="11" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="7" cy="11" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-horizontalRayLine" viewBox="0 0 22 22">
        <line x1="4" y1="11" x2="20" y2="11" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="4" cy="11" r="2" fill="currentColor"/>
        <path d="M18 9l3 2-3 2" stroke="currentColor" fill="none" stroke-width="1"/>
      </symbol>
      <symbol id="icon-horizontalSegment" viewBox="0 0 22 22">
        <line x1="4" y1="11" x2="18" y2="11" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="4" cy="11" r="2" fill="currentColor"/>
        <circle cx="18" cy="11" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-verticalStraightLine" viewBox="0 0 22 22">
        <line x1="11" y1="2" x2="11" y2="20" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="11" cy="11" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-verticalRayLine" viewBox="0 0 22 22">
        <line x1="11" y1="4" x2="11" y2="20" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="11" cy="4" r="2" fill="currentColor"/>
        <path d="M9 18l2 3 2-3" stroke="currentColor" fill="none" stroke-width="1"/>
      </symbol>
      <symbol id="icon-verticalSegment" viewBox="0 0 22 22">
        <line x1="11" y1="4" x2="11" y2="18" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="11" cy="4" r="2" fill="currentColor"/>
        <circle cx="11" cy="18" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-straightLine" viewBox="0 0 22 22">
        <line x1="3" y1="19" x2="19" y2="3" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="8" cy="14" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-rayLine" viewBox="0 0 22 22">
        <line x1="4" y1="18" x2="19" y2="3" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="4" cy="18" r="2" fill="currentColor"/>
        <path d="M17 3l2-1-1 2" stroke="currentColor" fill="none" stroke-width="1"/>
      </symbol>
      <symbol id="icon-segment" viewBox="0 0 22 22">
        <line x1="4" y1="18" x2="18" y2="4" stroke="currentColor" stroke-width="1.5"/>
        <circle cx="4" cy="18" r="2" fill="currentColor"/>
        <circle cx="18" cy="4" r="2" fill="currentColor"/>
      </symbol>
      <symbol id="icon-arrow" viewBox="0 0 22 22">
        <line x1="4" y1="18" x2="18" y2="4" stroke="currentColor" stroke-width="1.5"/>
        <path d="M14 4h5v5" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linejoin="round"/>
      </symbol>
      <symbol id="icon-priceLine" viewBox="0 0 22 22">
        <line x1="2" y1="11" x2="14" y2="11" stroke="currentColor" stroke-width="1.5"/>
        <rect x="14" y="7" width="6" height="8" rx="1" stroke="currentColor" stroke-width="1" fill="none"/>
        <text x="17" y="13" font-size="6" text-anchor="middle" fill="currentColor">$</text>
      </symbol>
      <!-- === 通道工具 === -->
      <symbol id="icon-priceChannelLine" viewBox="0 0 22 22">
        <line x1="3" y1="17" x2="19" y2="5" stroke="currentColor" stroke-width="1.2"/>
        <line x1="3" y1="20" x2="19" y2="8" stroke="currentColor" stroke-width="1.2"/>
        <circle cx="6" cy="15" r="1.5" fill="currentColor"/>
        <circle cx="16" cy="7" r="1.5" fill="currentColor"/>
      </symbol>
      <symbol id="icon-parallelStraightLine" viewBox="0 0 22 22">
        <line x1="3" y1="15" x2="19" y2="5" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="18" x2="19" y2="8" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="21" x2="19" y2="11" stroke="currentColor" stroke-width="1"/>
      </symbol>
      <!-- === 几何工具 === -->
      <symbol id="icon-circle" viewBox="0 0 22 22">
        <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-rect" viewBox="0 0 22 22">
        <rect x="3" y="5" width="16" height="12" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-parallelogram" viewBox="0 0 22 22">
        <polygon points="7,5 19,5 15,17 3,17" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-triangle" viewBox="0 0 22 22">
        <polygon points="11,4 20,18 2,18" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <!-- === 斐波那契工具 === -->
      <symbol id="icon-fibonacciLine" viewBox="0 0 22 22">
        <line x1="3" y1="4" x2="19" y2="4" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="8" x2="19" y2="8" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="11" x2="19" y2="11" stroke="currentColor" stroke-width="1" stroke-dasharray="2 2"/>
        <line x1="3" y1="14" x2="19" y2="14" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="18" x2="19" y2="18" stroke="currentColor" stroke-width="1"/>
      </symbol>
      <symbol id="icon-fibonacciSegment" viewBox="0 0 22 22">
        <line x1="5" y1="4" x2="17" y2="4" stroke="currentColor" stroke-width="1"/>
        <line x1="5" y1="8" x2="17" y2="8" stroke="currentColor" stroke-width="1"/>
        <line x1="5" y1="14" x2="17" y2="14" stroke="currentColor" stroke-width="1"/>
        <line x1="5" y1="18" x2="17" y2="18" stroke="currentColor" stroke-width="1"/>
        <circle cx="5" cy="4" r="1.5" fill="currentColor"/>
        <circle cx="17" cy="18" r="1.5" fill="currentColor"/>
      </symbol>
      <symbol id="icon-fibonacciCircle" viewBox="0 0 22 22">
        <circle cx="11" cy="11" r="4" stroke="currentColor" stroke-width="1" fill="none"/>
        <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1" fill="none"/>
        <circle cx="11" cy="11" r="9.5" stroke="currentColor" stroke-width="1" fill="none"/>
      </symbol>
      <symbol id="icon-fibonacciSpiral" viewBox="0 0 22 22">
        <path d="M11 11 Q11 7 15 7 Q19 7 19 11 Q19 18 11 18 Q2 18 2 11 Q2 2 11 2" stroke="currentColor" stroke-width="1.2" fill="none"/>
      </symbol>
      <symbol id="icon-fibonacciSpeedResistanceFan" viewBox="0 0 22 22">
        <line x1="3" y1="18" x2="19" y2="4" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="18" x2="19" y2="9" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="18" x2="19" y2="14" stroke="currentColor" stroke-width="1"/>
        <circle cx="3" cy="18" r="1.5" fill="currentColor"/>
      </symbol>
      <symbol id="icon-fibonacciExtension" viewBox="0 0 22 22">
        <line x1="4" y1="5" x2="18" y2="5" stroke="currentColor" stroke-width="1"/>
        <line x1="4" y1="11" x2="18" y2="11" stroke="currentColor" stroke-width="1"/>
        <line x1="4" y1="17" x2="18" y2="17" stroke="currentColor" stroke-width="1"/>
        <polyline points="5,17 10,5 14,11" stroke="currentColor" stroke-width="1.2" fill="none"/>
      </symbol>
      <symbol id="icon-gannBox" viewBox="0 0 22 22">
        <rect x="3" y="3" width="16" height="16" stroke="currentColor" stroke-width="1" fill="none"/>
        <line x1="3" y1="3" x2="19" y2="19" stroke="currentColor" stroke-width="1"/>
        <line x1="3" y1="19" x2="19" y2="3" stroke="currentColor" stroke-width="1"/>
        <line x1="11" y1="3" x2="11" y2="19" stroke="currentColor" stroke-width="0.8" stroke-dasharray="2 2"/>
        <line x1="3" y1="11" x2="19" y2="11" stroke="currentColor" stroke-width="0.8" stroke-dasharray="2 2"/>
      </symbol>
      <!-- === 浪型工具 === -->
      <symbol id="icon-xabcd" viewBox="0 0 22 22">
        <polyline points="2,14 6,5 10,12 15,4 20,16" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <text x="2" y="18" font-size="4" fill="currentColor">X</text>
        <text x="6" y="4" font-size="4" fill="currentColor">A</text>
        <text x="10" y="16" font-size="4" fill="currentColor">B</text>
        <text x="15" y="3" font-size="4" fill="currentColor">C</text>
        <text x="19" y="20" font-size="4" fill="currentColor">D</text>
      </symbol>
      <symbol id="icon-abcd" viewBox="0 0 22 22">
        <polyline points="3,6 8,16 14,6 19,16" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <text x="2" y="5" font-size="4.5" fill="currentColor">A</text>
        <text x="7" y="20" font-size="4.5" fill="currentColor">B</text>
        <text x="13" y="5" font-size="4.5" fill="currentColor">C</text>
        <text x="18" y="20" font-size="4.5" fill="currentColor">D</text>
      </symbol>
      <symbol id="icon-threeWaves" viewBox="0 0 22 22">
        <polyline points="3,16 7,6 13,14 19,4" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <text x="11" y="20" font-size="5" text-anchor="middle" fill="currentColor">3</text>
      </symbol>
      <symbol id="icon-fiveWaves" viewBox="0 0 22 22">
        <polyline points="2,14 5,6 8,12 12,4 16,10 20,5" stroke="currentColor" stroke-width="1.2" fill="none"/>
        <text x="11" y="20" font-size="5" text-anchor="middle" fill="currentColor">5</text>
      </symbol>
      <symbol id="icon-eightWaves" viewBox="0 0 22 22">
        <polyline points="1,12 3,6 5,10 8,3 10,8 13,5 16,9 18,4 21,11" stroke="currentColor" stroke-width="1" fill="none"/>
        <text x="11" y="20" font-size="5" text-anchor="middle" fill="currentColor">8</text>
      </symbol>
      <symbol id="icon-anyWaves" viewBox="0 0 22 22">
        <polyline points="2,14 6,6 10,12 14,4 18,10" stroke="currentColor" stroke-width="1.2" fill="none"/>
        <text x="11" y="20" font-size="5" text-anchor="middle" fill="currentColor">∞</text>
      </symbol>
      <!-- === 磁吸模式 === -->
      <symbol id="icon-weak_magnet" viewBox="0 0 22 22">
        <path d="M7 3v5a4 4 0 0 0 8 0V3" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <line x1="7" y1="5" x2="7" y2="3" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        <line x1="15" y1="5" x2="15" y2="3" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        <path d="M4 14l3-2M18 14l-3-2" stroke="currentColor" stroke-width="1" stroke-dasharray="2 1"/>
      </symbol>
      <symbol id="icon-strong_magnet" viewBox="0 0 22 22">
        <path d="M7 3v5a4 4 0 0 0 8 0V3" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <line x1="7" y1="5" x2="7" y2="3" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        <line x1="15" y1="5" x2="15" y2="3" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
        <path d="M3 16l4-4M19 16l-4-4M3 13l4-3M19 13l-4-3" stroke="currentColor" stroke-width="1.2"/>
      </symbol>
      <!-- === 工具按钮 === -->
      <symbol id="icon-lock" viewBox="0 0 22 22">
        <rect x="5" y="10" width="12" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M8 10V7a3 3 0 0 1 6 0v3" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-unlock" viewBox="0 0 22 22">
        <rect x="5" y="10" width="12" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M8 10V7a3 3 0 0 1 6 0" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-visible" viewBox="0 0 22 22">
        <ellipse cx="11" cy="11" rx="9" ry="5" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <circle cx="11" cy="11" r="2.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
      </symbol>
      <symbol id="icon-invisible" viewBox="0 0 22 22">
        <ellipse cx="11" cy="11" rx="9" ry="5" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <circle cx="11" cy="11" r="2.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <line x1="4" y1="18" x2="18" y2="4" stroke="currentColor" stroke-width="1.5"/>
      </symbol>
      <symbol id="icon-remove" viewBox="0 0 22 22">
        <line x1="7" y1="7" x2="15" y2="15" stroke="currentColor" stroke-width="1.8"/>
        <line x1="15" y1="7" x2="7" y2="15" stroke="currentColor" stroke-width="1.8"/>
      </symbol>
    </defs>
  </svg>

  <div class="klinecharts-pro" data-theme="dark">
    <!-- ===== Period Bar (顶部工具栏) ===== -->
    <div class="klinecharts-pro-period-bar">
      <!-- 折叠/展开画线栏按钮 -->
      <div class="menu-container" @click="toggleDrawingBar">
        <svg :class="{ rotate: !drawingBarVisible }" viewBox="0 0 1024 1024">
          <path d="M192 288h640c17.7 0 32-14.3 32-32s-14.3-32-32-32H192c-17.7 0-32 14.3-32 32s14.3 32 32 32zm246 224H832c17.7 0 32-14.3 32-32s-14.3-32-32-32H438c-17.7 0-32 14.3-32 32s14.3 32 32 32zm394 224H192c-17.7 0-32 14.3-32 32s14.3 32 32 32h640c17.7 0 32-14.3 32-32s-14.3-32-32-32zM319 352l-160 160 160 160z"/>
        </svg>
      </div>

      <!-- 交易对名称 -->
      <div class="symbol">
        <span>{{ displaySymbol }}</span>
      </div>

      <!-- 周期按钮 -->
      <span
        v-for="p in periods" :key="p.value"
        :class="['item', 'period', { selected: currentInterval === p.value }]"
        @click="switchPeriod(p.value)"
      >{{ p.label }}</span>

      <!-- 指标按钮 -->
      <div class="item tools" @click="indicatorModalVisible = !indicatorModalVisible">
        <svg viewBox="0 0 20 20">
          <path d="M15.9 20H3.7C1.6 20 0 18.4 0 16.3V3.7C0 1.6 1.6 0 3.7 0h12.2C17.9 0 19.5 1.6 19.5 3.7c0 .6-.3.8-1 .8-.6 0-1-.3-1-.8 0-1-1.6-1.8-1.6-1.8H3.7c-1 0-1.8.8-1.8 1.8v12.6c0 1 .8 1.8 1.8 1.8h12.2c1 0 1.8-.8 1.8-1.8 0-.5.5-1 1-1s1 .5 1 1c0 2-1.6 3.7-3.7 3.7zM14.9 12.9c-.2 0-.5 0-.6-.2l-3-3.5c-.3-.3-.3-.8 0-1.1.3-.3.8-.3 1.1 0l3 3.4c.3.3.3.8 0 1.1 0 .2-.2.3-.5.3zm-3.5.3c-.2 0-.3 0-.5-.2-.3-.3-.3-.6 0-1l4.1-4.3c.3-.3.7-.3 1-.1.4.3.4.7.1 1l-4.1 4.4c-.2.1-.4.2-.6.2zm-1.1-9.5c.3 0 1.1.2 1.1 1 0 .6-1 .5-1.3.5-1.4 0-1.9.8-2.1 1.4l-.3 1.9h1.6c.3 0 .6.3.6.6 0 .3-.3.6-.6.6h-1.7L7 14.8c-.2 1.5-1.1 1.5-2 1.5s-1-1.5-.5-1.5l1.1-4.8H4.6c-.3 0-.6-.3-.6-.6 0-.3.3-.6.6-.6h1.7l.5-2.1c.3-2.7 2.7-2.9 3.5-2.7zm8.1 2.9c.2-.5.5-1 1-.6.5.2.6.5.6 1L18.4 13.4c-.2.5-.7.6-1.2.6-.5-.2-.6-.5-.6-1l1.6-6.4z"/>
        </svg>
        <span>指标</span>
      </div>

      <!-- 截图按钮 -->
      <div class="item tools" @click="takeScreenshot">
        <svg viewBox="0 0 20 20">
          <path d="M6.5 1h7.4c.1 0 .3.1.3.3l.2 1.3c.1.6.6 1 1.2 1H18c1.4 0 2.5 1.2 2.5 2.6v10.3c0 1.4-1.1 2.6-2.5 2.6H2.5C1.1 19 0 17.8 0 16.4V6.1c0-1.4 1.1-2.6 2.5-2.6h2.2c.6 0 1.1-.4 1.2-1l.2-1.3c0-.1.2-.3.3-.3zm8.8 3.9c-.7 0-2.2.9-2.5 2.1l-.1.5H7.3l-.1-.5c-.2-1.2-1-2.1-2.2-2.1H2.5c-.7 0-1.3.6-1.3 1.3v10.3c0 .7.6 1.3 1.3 1.3h15c.7 0 1.3-.6 1.3-1.3V6.1c0-.7-.6-1.3-1.3-1.3h-2.2zM4.4 6.8H3.1c-.3 0-.6-.3-.6-.6 0-.4.3-.6.6-.6h1.3c.3 0 .6.3.6.6 0 .3-.3.6-.6.6zM10 6.1c-3 0-5.3 2.4-5.3 5.5S7 17.1 10 17.1s5.3-2.4 5.3-5.5S13 6.1 10 6.1zm0 1.3c1.1 0 2.1.4 2.9 1.2.8.8 1.2 1.8 1.2 3s-.4 2.2-1.2 3c-.8.8-1.8 1.2-2.9 1.2s-2.1-.4-2.9-1.2c-.8-.8-1.2-1.8-1.2-3s.4-2.2 1.2-3c.8-.8 1.8-1.2 2.9-1.2z"/>
        </svg>
        <span>截图</span>
      </div>

      <!-- 全屏按钮 -->
      <div class="item tools" @click="toggleFullScreen">
        <svg v-if="!isFullScreen" viewBox="0 0 20 20">
          <path d="M2.9 1.8l4.6 4.6-1.2 1.2L1.8 2.9 0 4.7V0h4.7L2.9 1.8zm3.5 10.6L1.8 17l0-2.7H0v5h5v-1.8l-2.7 0 4.6-4.6-1.2-1.2zM15.3 0l1.8 1.8-4.6 4.6 1.2 1.2 4.6-4.6L20 4.7V0h-4.7zm-1.7 12.4l-1.2 1.2 4.6 4.6-1.8 1.8H20v-4.7l-1.8 1.8-4.6-4.6z"/>
        </svg>
        <svg v-else viewBox="0 0 20 20">
          <path d="M1.1 0L0 1.1l4.2 5.3L2.5 6.9 6.9 6.9 6.9 2.6 5.3 4.2 1.1 0zM15.8 5.3L20 1.1 18.9 0 14.7 4.2 13.1 2.6 13.1 6.9 17.5 6.9 15.8 5.3zM4.2 14.7L0.1 18.8 1.2 20 5.3 15.8 6.9 17.4 6.9 13.1 2.5 13.1 4.2 14.7zM17.5 13.1L13.1 13.1 13.1 17.4 14.7 15.8 18.8 20 19.9 18.8 15.8 14.7 17.5 13.1z"/>
        </svg>
        <span>{{ isFullScreen ? '退出全屏' : '全屏' }}</span>
      </div>
    </div>

    <!-- ===== Content (画线栏 + 图表) ===== -->
    <div class="klinecharts-pro-content">
      <!-- 加载指示器 -->
      <div v-if="loadingVisible" class="loading-mask">
        <div class="loading-spinner" />
      </div>

      <!-- Drawing Bar (左侧画线工具栏) -->
      <div v-show="drawingBarVisible" class="klinecharts-pro-drawing-bar">
        <!-- 5 个画线工具组 -->
        <div
          v-for="group in overlayGroups" :key="group.key"
          class="item" tabindex="0"
          @blur="popoverKey = ''"
        >
          <!-- 主图标：点击直接使用当前选中工具 -->
          <span class="icon-overlay" @click="onDrawingItemClick(group.icon)">
            <svg viewBox="0 0 22 22"><use :href="'#icon-' + group.icon" /></svg>
          </span>

          <!-- 展开箭头 -->
          <div class="icon-arrow" @click.stop="togglePopover(group.key)">
            <svg :class="{ rotate: popoverKey === group.key }" viewBox="0 0 4 6">
              <path d="M1.07 0.16C0.83-0.05 0.43-0.05 0.18 0.16C-0.06 0.37-0.06 0.72 0.18 0.93L2.61 3.03L0.26 5.07C0.01 5.28 0.01 5.63 0.26 5.84C0.51 6.05 0.9 6.05 1.15 5.84L3.82 3.53C4.02 3.36 4.05 3.09 3.92 2.88C3.93 2.73 3.87 2.58 3.74 2.47L1.07 0.16Z"/>
            </svg>
          </div>

          <!-- 弹出工具列表 -->
          <ul v-if="popoverKey === group.key" class="list">
            <li
              v-for="tool in group.list" :key="tool.key"
              @click.stop="selectDrawingTool(group, tool)"
            >
              <svg class="tool-icon" viewBox="0 0 22 22"><use :href="'#icon-' + tool.key" /></svg>
              <span class="tool-text">{{ tool.text }}</span>
            </li>
          </ul>
        </div>

        <span class="split-line" />

        <!-- 磁吸模式 -->
        <div class="item" tabindex="0" @blur="popoverKey = ''">
          <span :class="['icon-overlay', { selected: drawingMode !== 'normal' }]" @click="onMagnetModeClick">
            <svg viewBox="0 0 22 22"><use :href="'#icon-' + magnetIcon" /></svg>
          </span>
          <div class="icon-arrow" @click.stop="popoverKey = popoverKey === 'magnet' ? '' : 'magnet'">
            <svg :class="{ rotate: popoverKey === 'magnet' }" viewBox="0 0 4 6">
              <path d="M1.07 0.16C0.83-0.05 0.43-0.05 0.18 0.16C-0.06 0.37-0.06 0.72 0.18 0.93L2.61 3.03L0.26 5.07C0.01 5.28 0.01 5.63 0.26 5.84C0.51 6.05 0.9 6.05 1.15 5.84L3.82 3.53C4.02 3.36 4.05 3.09 3.92 2.88C3.93 2.73 3.87 2.58 3.74 2.47L1.07 0.16Z"/>
            </svg>
          </div>
          <ul v-if="popoverKey === 'magnet'" class="list">
            <li v-for="m in magnetTools" :key="m.key" @click.stop="selectMagnetMode(m)">
              <svg class="tool-icon" viewBox="0 0 22 22"><use :href="'#icon-' + m.key" /></svg>
              <span class="tool-text">{{ m.text }}</span>
            </li>
          </ul>
        </div>

        <!-- 锁定 -->
        <div class="item">
          <span :class="['icon-overlay', { selected: drawingLock }]" @click="onOverlayLockChange">
            <svg viewBox="0 0 22 22"><use :href="drawingLock ? '#icon-lock' : '#icon-unlock'" /></svg>
          </span>
        </div>

        <!-- 可见性 -->
        <div class="item">
          <span :class="['icon-overlay', { selected: !drawingVisible }]" @click="onOverlayVisibleChange">
            <svg viewBox="0 0 22 22"><use :href="drawingVisible ? '#icon-visible' : '#icon-invisible'" /></svg>
          </span>
        </div>

        <span class="split-line" />

        <!-- 删除全部 -->
        <div class="item">
          <span class="icon-overlay" @click="removeAllOverlays">
            <svg viewBox="0 0 22 22"><use href="#icon-remove" /></svg>
          </span>
        </div>
      </div>

      <!-- 图表容器 -->
      <div ref="chartContainer" class="klinecharts-pro-widget" :data-drawing-bar-visible="drawingBarVisible" />
    </div>

    <!-- ===== 指标选择弹窗 ===== -->
    <div v-if="indicatorModalVisible" class="indicator-modal-mask" @click.self="indicatorModalVisible = false">
      <div class="indicator-modal">
        <div class="modal-header">
          <span>指标</span>
          <span class="modal-close" @click="indicatorModalVisible = false">✕</span>
        </div>
        <div class="modal-body">
          <div class="indicator-section">
            <div class="section-title">主图指标</div>
            <div class="indicator-grid">
              <div
                v-for="name in mainIndicatorList" :key="name"
                :class="['indicator-chip', { active: activeMainIndicators.has(name) }]"
                @click="toggleMainIndicator(name)"
              >{{ name }}</div>
            </div>
          </div>
          <div class="indicator-section">
            <div class="section-title">副图指标</div>
            <div class="indicator-grid">
              <div
                v-for="name in subIndicatorList" :key="name"
                :class="['indicator-chip', { active: activeSubIndicators.has(name) }]"
                @click="toggleSubIndicator(name)"
              >{{ name }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 指标参数设置弹窗 ===== -->
    <div v-if="indicatorSettingModal.visible" class="indicator-modal-mask" @click.self="closeIndicatorSetting">
      <div class="indicator-setting-modal">
        <div class="modal-header">
          <span>{{ indicatorSettingModal.indicatorName }} 参数设置</span>
          <span class="modal-close" @click="closeIndicatorSetting">✕</span>
        </div>
        <div class="modal-body">
          <div
            v-for="(param, idx) in indicatorSettingModal.calcParams" :key="idx"
            class="setting-row"
          >
            <label class="setting-label">
              {{ (indicatorParamConfig[indicatorSettingModal.indicatorName] && indicatorParamConfig[indicatorSettingModal.indicatorName][idx])
                   ? indicatorParamConfig[indicatorSettingModal.indicatorName][idx].paramNameKey
                   : '参数' + (idx + 1) }}
            </label>
            <div class="setting-input-group">
              <button class="spin-btn" @click="indicatorSettingModal.calcParams[idx] = Math.max(1, Number(indicatorSettingModal.calcParams[idx]) - 1)">−</button>
              <input
                type="number"
                class="setting-input"
                :value="param"
                :min="(indicatorParamConfig[indicatorSettingModal.indicatorName] && indicatorParamConfig[indicatorSettingModal.indicatorName][idx])
                        ? indicatorParamConfig[indicatorSettingModal.indicatorName][idx].min : 1"
                @input="indicatorSettingModal.calcParams[idx] = Number($event.target.value)"
              />
              <button class="spin-btn" @click="indicatorSettingModal.calcParams[idx] = Number(indicatorSettingModal.calcParams[idx]) + 1">+</button>
            </div>
          </div>
          <div v-if="indicatorSettingModal.calcParams.length === 0" class="setting-empty">
            此指标没有可调参数
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeIndicatorSetting">取消</button>
          <button class="btn-confirm" @click="confirmIndicatorSetting">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== 根容器 (Pro 风格 CSS 变量) ===== */
.klinecharts-pro {
  --pro-primary: #1677ff;
  --pro-hover-bg: rgba(22, 119, 255, 0.15);
  --pro-bg: #151517;
  --pro-popover-bg: #1c1c1f;
  --pro-text: #f8f8f8;
  --pro-text-second: #929AA5;
  --pro-border: #292929;
  --pro-selected: rgba(22, 119, 255, 0.15);

  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  color: var(--pro-text);
  background-color: var(--pro-bg);
  font-size: 14px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
}

/* ===== Period Bar (顶部工具栏) ===== */
.klinecharts-pro-period-bar {
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 38px;
  width: 100%;
  box-sizing: border-box;
  border-bottom: solid 1px var(--pro-border);
  flex-shrink: 0;
  user-select: none;
}

.menu-container {
  display: flex;
  height: 100%;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  width: 52px;
  box-sizing: border-box;
  border-right: solid 1px var(--pro-border);
  flex-shrink: 0;
}
.menu-container svg {
  fill: var(--pro-text);
  width: 22px;
  height: 22px;
  cursor: pointer;
  transition: transform 0.2s;
}
.menu-container svg.rotate {
  transform: rotate(180deg);
}

.symbol {
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 100%;
  font-size: 16px;
  padding: 0 12px;
  font-weight: bold;
  box-sizing: border-box;
  border-right: solid 1px var(--pro-border);
  cursor: default;
  white-space: nowrap;
}

.klinecharts-pro-period-bar .item {
  transition: all 0.2s;
  box-sizing: border-box;
  cursor: pointer;
  fill: var(--pro-text-second);
  color: var(--pro-text-second);
}
.klinecharts-pro-period-bar .item.selected {
  background-color: var(--pro-selected) !important;
  color: var(--pro-primary);
}

.period {
  padding: 2px 6px;
  margin: 0 4px;
  border-radius: 2px;
  font-size: 13px;
}
.period:hover {
  background-color: var(--pro-hover-bg);
}
.period:first-of-type {
  margin-left: 12px;
}

.tools {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 0 12px;
  border-right: solid 1px var(--pro-border);
  font-size: 13px;
  white-space: nowrap;
}
.tools:hover {
  fill: var(--pro-primary);
  color: var(--pro-primary);
}
.tools svg {
  width: 16px;
  height: 16px;
  margin-right: 4px;
  flex-shrink: 0;
}
.period + .tools {
  border-left: solid 1px var(--pro-border);
  margin-left: 8px;
}

/* ===== Content ===== */
.klinecharts-pro-content {
  position: relative;
  display: flex;
  flex-direction: row;
  width: 100%;
  height: calc(100% - 38px);
}

/* ===== Loading ===== */
.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  background: rgba(21, 21, 23, 0.5);
}
.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--pro-border);
  border-top-color: var(--pro-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Drawing Bar (左侧画线工具栏) ===== */
.klinecharts-pro-drawing-bar {
  width: 52px;
  height: 100%;
  box-sizing: border-box;
  border-right: solid 1px var(--pro-border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 4px;
}

.klinecharts-pro-drawing-bar .item {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  position: relative;
  width: 100%;
  margin-top: 8px;
  cursor: pointer;
  color: var(--pro-text-second);
  fill: var(--pro-text-second);
  stroke: var(--pro-text-second);
}

.icon-overlay {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  transition: all 0.2s;
}
.icon-overlay svg {
  width: 24px;
  height: 24px;
}
.icon-overlay:hover {
  background-color: var(--pro-hover-bg);
}

.icon-arrow {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 0;
  right: 0;
  height: 32px;
  width: 10px;
  opacity: 0;
  transition: all 0.2s;
  border-top-left-radius: 2px;
  border-bottom-left-radius: 2px;
  z-index: 10;
}
.icon-arrow svg {
  width: 4px;
  height: 6px;
  fill: var(--pro-text-second);
  transition: transform 0.2s;
}
.icon-arrow svg.rotate {
  transform: rotate(180deg);
}
.icon-arrow:hover {
  background-color: var(--pro-hover-bg);
}

.klinecharts-pro-drawing-bar .item:hover .icon-arrow {
  opacity: 1;
}

.klinecharts-pro-drawing-bar .list {
  position: absolute;
  top: 0;
  left: calc(100% + 1px);
  white-space: nowrap;
  background-color: var(--pro-popover-bg);
  z-index: 99;
  box-shadow: 0 6px 12px 0 rgba(0, 0, 0, 0.3);
  min-height: auto;
  max-height: 320px;
  list-style: none;
  margin: 0;
  padding: 4px 0;
  border-radius: 4px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.2) transparent;
}
.klinecharts-pro-drawing-bar .list::-webkit-scrollbar {
  width: 4px;
}
.klinecharts-pro-drawing-bar .list::-webkit-scrollbar-track {
  background: transparent;
}
.klinecharts-pro-drawing-bar .list::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
}
.klinecharts-pro-drawing-bar .list::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.35);
}
.klinecharts-pro-drawing-bar .list li {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  cursor: pointer;
  color: var(--pro-text-second);
  font-size: 13px;
  transition: background-color 0.15s;
  gap: 8px;
}
.klinecharts-pro-drawing-bar .list li .tool-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: var(--pro-text-second);
}
.klinecharts-pro-drawing-bar .list li .tool-text {
  white-space: nowrap;
}
.klinecharts-pro-drawing-bar .list li:hover {
  background-color: var(--pro-hover-bg);
  color: var(--pro-text);
}
.klinecharts-pro-drawing-bar .list li:hover .tool-icon {
  color: var(--pro-text);
}

.icon-overlay.selected {
  color: var(--pro-primary);
  fill: var(--pro-primary);
}

.split-line {
  display: block;
  width: 100%;
  height: 1px;
  background-color: var(--pro-border);
  margin-top: 8px;
  flex-shrink: 0;
}

/* ===== Chart Widget ===== */
.klinecharts-pro-widget {
  width: calc(100% - 52px);
  height: 100%;
  margin-left: 0;
}
.klinecharts-pro-widget[data-drawing-bar-visible="false"] {
  width: 100%;
}

/* ===== 指标选择弹窗 ===== */
.indicator-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.indicator-modal {
  background-color: var(--pro-popover-bg);
  border: 1px solid var(--pro-border);
  border-radius: 8px;
  width: 480px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--pro-border);
  font-size: 16px;
  font-weight: 600;
}
.modal-close {
  cursor: pointer;
  color: var(--pro-text-second);
  font-size: 18px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s;
}
.modal-close:hover {
  background-color: var(--pro-hover-bg);
  color: var(--pro-text);
}
.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
}
.indicator-section {
  margin-bottom: 16px;
}
.section-title {
  color: var(--pro-text-second);
  font-size: 12px;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.indicator-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.indicator-chip {
  padding: 5px 14px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  background-color: rgba(255, 255, 255, 0.05);
  color: var(--pro-text-second);
  border: 1px solid transparent;
  transition: all 0.15s;
}
.indicator-chip:hover {
  background-color: var(--pro-hover-bg);
  color: var(--pro-text);
}
.indicator-chip.active {
  background-color: var(--pro-selected);
  color: var(--pro-primary);
  border-color: var(--pro-primary);
}

/* ===== 指标参数设置弹窗 ===== */
.indicator-setting-modal {
  background-color: var(--pro-popover-bg);
  border: 1px solid var(--pro-border);
  border-radius: 8px;
  width: 360px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.setting-label {
  color: var(--pro-text-second);
  font-size: 13px;
  min-width: 70px;
}
.setting-input {
  width: 120px;
  padding: 6px 10px;
  border: 1px solid var(--pro-border);
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.06);
  color: var(--pro-text);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  color-scheme: dark;
  -moz-appearance: textfield;
}
.setting-input:focus {
  border-color: var(--pro-primary);
}
.setting-input::-webkit-inner-spin-button,
.setting-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.setting-input-group {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--pro-border);
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.15s;
}
.setting-input-group:focus-within {
  border-color: var(--pro-primary);
}
.setting-input-group .setting-input {
  border: none;
  border-radius: 0;
  width: 80px;
  text-align: center;
  border-left: 1px solid var(--pro-border);
  border-right: 1px solid var(--pro-border);
}
.setting-input-group .setting-input:focus {
  border-color: var(--pro-border);
}
.spin-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 30px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--pro-text-second);
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  flex-shrink: 0;
  transition: all 0.15s;
}
.spin-btn:hover {
  background: var(--pro-hover-bg);
  color: var(--pro-text);
}
.spin-btn:active {
  background: rgba(22, 119, 255, 0.25);
}
.setting-empty {
  color: var(--pro-text-second);
  font-size: 13px;
  text-align: center;
  padding: 12px 0;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--pro-border);
}
.btn-cancel, .btn-confirm {
  padding: 6px 20px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}
.btn-cancel {
  background-color: rgba(255, 255, 255, 0.08);
  color: var(--pro-text-second);
}
.btn-cancel:hover {
  background-color: rgba(255, 255, 255, 0.12);
  color: var(--pro-text);
}
.btn-confirm {
  background-color: var(--pro-primary);
  color: #fff;
}
.btn-confirm:hover {
  background-color: #4096ff;
}
</style>
