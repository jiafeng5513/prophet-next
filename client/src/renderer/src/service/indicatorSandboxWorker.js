/**
 * Web Worker 沙箱 - 用于安全验证自定义指标代码
 *
 * 在隔离环境中执行用户代码，验证语法正确性和接口合规性。
 * 不暴露 DOM、Node、网络等危险 API。
 */

// 禁止危险 API
self.fetch = undefined
self.XMLHttpRequest = undefined
self.WebSocket = undefined
self.importScripts = undefined

// 最小化 PineJS.Std 模拟（仅用于接口验证）
const PineJSMock = {
  Std: {
    close: () => 0,
    open: () => 0,
    high: () => 0,
    low: () => 0,
    volume: () => 0,
    hlc3: () => 0,
    ohlc4: () => 0,
    hl2: () => 0,
    ema: () => 0,
    sma: () => 0,
    rsi: () => 0,
    macd: () => [0, 0, 0],
    atr: () => 0,
    tr: () => 0,
    stoch: () => 0,
    bb: () => [0, 0, 0],
    wma: () => 0,
    vwma: () => 0,
    highest: () => 0,
    lowest: () => 0,
    cross: () => false,
    crossover: () => false,
    crossunder: () => false,
  }
}

self.onmessage = function (e) {
  const { code, action } = e.data

  if (action === 'validate') {
    try {
      // 用 Function 构造器在 Worker 内执行（双层隔离）
      const factory = new Function(
        'PineJS',
        `"use strict";\n${code}\nif (typeof create !== 'function') { throw new Error('必须定义 create(PineJS) 函数'); }\nreturn create(PineJS);`
      )

      const indicator = factory(PineJSMock)

      // 结构验证
      if (!indicator || typeof indicator !== 'object') {
        self.postMessage({ success: false, error: 'create() 必须返回一个对象' })
        return
      }

      if (!indicator.name || typeof indicator.name !== 'string') {
        self.postMessage({ success: false, error: '指标对象缺少 name 字段' })
        return
      }

      if (!indicator.metainfo || typeof indicator.metainfo !== 'object') {
        self.postMessage({ success: false, error: '指标对象缺少 metainfo 字段' })
        return
      }

      if (!indicator.constructor || typeof indicator.constructor !== 'function') {
        self.postMessage({ success: false, error: '指标对象缺少 constructor 函数' })
        return
      }

      // 验证 metainfo 必要字段
      const meta = indicator.metainfo
      if (!meta.id || !meta.plots || !Array.isArray(meta.plots)) {
        self.postMessage({ success: false, error: 'metainfo 需包含 id 和 plots 数组' })
        return
      }

      self.postMessage({
        success: true,
        metainfo: {
          name: indicator.name,
          id: meta.id,
          plots: meta.plots.length,
          is_price_study: meta.is_price_study ?? true
        }
      })
    } catch (err) {
      self.postMessage({ success: false, error: err.message })
    }
  }
}
