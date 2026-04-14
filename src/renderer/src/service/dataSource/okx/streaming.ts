/// <reference types="@tradingview/trading_platform/charting_library/datafeed-api" />
import { parseFullSymbol } from './helpers'

// OKX REST API 和 WebSocket 使用的周期格式
// REST API 的 bar 参数和 WebSocket 的 channel 周期格式应该一致
export const OKX_RESOLUSION = {
  1: '1m',   // 1分钟
  3: '3m',   // 3分钟
  5: '5m',   // 5分钟
  15: '15m', // 15分钟
  30: '30m', // 30分钟（如果需要）
  60: '1H',  // 1小时（OKX 使用大写 H）
  120: '2H', // 2小时
  240: '4H', // 4小时
  360: '6H', // 6小时
  720: '12H', // 12小时
  '1D': '1D', // 1天
  '2D': '2D', // 2天
  '3D': '3D', // 3天
  '1W': '1W', // 1周
  '1M': '1M'  // 1月
}

// OKX WebSocket 订阅支持的周期格式映射
// 根据 OKX API 文档，WebSocket 支持的周期格式应该与 REST API 一致
// 使用与 REST API 相同的周期格式
// 注意：如果某个周期不支持，可以临时映射到支持的周期进行测试
export const OKX_WS_RESOLUTION = {
  1: '1m',   // 1分钟
  3: '3m',   // 3分钟
  5: '5m',   // 5分钟
  15: '1H',  // 15分钟 -> 临时映射到 1H 进行测试
  30: '30m', // 30分钟
  60: '1H',  // 1小时（OKX 使用大写 H）
  120: '2H', // 2小时
  240: '4H', // 4小时
  360: '6H', // 6小时
  720: '12H', // 12小时
  '1D': '1D', // 1天
  '2D': '1D', // 2天 -> 映射到 1D（如果 WebSocket 不支持）
  '3D': '1D', // 3天 -> 映射到 1D（如果 WebSocket 不支持）
  '1W': '1W', // 1周
  '1M': '1M'  // 1月
}

export default class SocketClient {
  socket!: WebSocket;
  channelToSubscription!: Map<string, any>;

  constructor() {
    console.log("[SocketClient] init");
    this._createSocket();
  }

  _createSocket() {
    console.log('[SocketClient] _createSocket')
    // OKX WebSocket 公共频道端点
    // 根据 OKX API 文档，WebSocket URL 格式为: wss://ws.okx.com:8443/ws/v5/public
    // 注意：必须使用 8443 端口，这是 OKX WebSocket 的标准端口
    const wsUrl = 'wss://ws.okx.com:8443/ws/v5/public'
    console.log('[SocketClient] Connecting to WebSocket:', wsUrl)
    this.socket = new WebSocket(wsUrl)
    this.channelToSubscription = new Map()

    this.socket.onopen = () => {
      console.log('[socket] Connected to OKX WebSocket')
    }

    this.socket.onclose = (event) => {
      console.log('[socket] Disconnected:', event.code, event.reason)
      // 可以在这里实现重连逻辑
    }

    this.socket.onerror = (error) => {
      console.error('[socket] Error:', error)
    }

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[socket] Received message:', data)

        // 处理订阅响应
        if (data.event) {
          if (data.event === 'subscribe' && data.code === '0') {
            console.log('[socket] Subscription successful:', data.arg)
            return
          }
          if (data.event === 'unsubscribe' && data.code === '0') {
            console.log('[socket] Unsubscription successful:', data.arg)
            return
          }
          if (data.event === 'error') {
            console.error('[socket] Error event:', data)
            console.error('[socket] Error code:', data.code)
            console.error('[socket] Error message:', data.msg)
            console.error('[socket] Error arg:', data.arg)
            // 如果是订阅错误，尝试重新订阅或使用不同的格式
            if (data.arg && data.arg.channel) {
              console.error('[socket] Failed to subscribe to channel:', data.arg.channel, 'instId:', data.arg.instId)
            }
            return
          }
        }

        // 处理K线数据
        // OKX WebSocket 数据格式: { arg: { channel: "candle1m", instId: "BTC-USDT" }, data: [[...]] }
        if (data.arg && data.arg.channel && data.arg.channel.startsWith('candle') && data.data) {
          const { channel, instId } = data.arg
          const klineData = data.data[0] // 取第一条数据

          if (!klineData || klineData.length < 6) {
            console.log('[socket] Invalid kline data format')
            return
          }

          const channelString = `${channel}~${instId}`
          const subscriptionItem = this.channelToSubscription.get(channelString)

          if (!subscriptionItem || !subscriptionItem.lastDailyBar) {
            console.log('[socket] No subscription found for', channelString)
            return
          }

          const lastDailyBar = subscriptionItem.lastDailyBar
          const barStartTime = parseInt(klineData[0]) // 时间戳（毫秒）
          const barEndTime = parseInt(klineData[0]) // OKX 返回的是K线开始时间
          const isBarClosed = klineData[8] === '1' // 是否完结（1表示完结，0表示进行中）

          let bar: {
            time: number
            open: number
            high: number
            low: number
            close: number
            volume?: number
          }

          if (isBarClosed) {
            // K线已完结，创建新的bar
            bar = {
              time: barStartTime,
              open: parseFloat(klineData[1]),
              high: parseFloat(klineData[2]),
              low: parseFloat(klineData[3]),
              close: parseFloat(klineData[4]),
              volume: parseFloat(klineData[5])
            }
            console.log('[socket] New bar closed:', bar)
            subscriptionItem.lastDailyBar = bar
          } else {
            // K线还在更新中，更新当前bar
            bar = {
              time: barStartTime,
              open: parseFloat(klineData[1]),
              high: parseFloat(klineData[2]),
              low: parseFloat(klineData[3]),
              close: parseFloat(klineData[4]),
              volume: parseFloat(klineData[5])
            }
            console.log('[socket] Bar updated:', bar)
            subscriptionItem.lastDailyBar = bar
          }

          // 发送数据给所有订阅者
          subscriptionItem.handlers.forEach((handler: { callback: (arg0: any) => any }) => {
            handler.callback(bar)
          })
        }
      } catch (error) {
        console.error('[socket] Error parsing message:', error, event.data)
      }
    }
  }

  public subscribeOnStream(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    onRealtimeCallback: TradingView.SubscribeBarsCallback,
    subscriberUID: string,
    onResetCacheNeededCallback: () => void,
    lastDailyBar: TradingView.Bar | undefined
  ) {
    // 使用 ticker 或 name，确保能正确解析
    const symbolToParse = symbolInfo.ticker || symbolInfo.name || symbolInfo.full_name || ''
    console.log(`[subscribeOnStream] Parsing symbol - ticker: ${symbolInfo.ticker}, name: ${symbolInfo.name}, full_name: ${symbolInfo.full_name}`)
    const parsedSymbol = parseFullSymbol(symbolToParse)
    if (!parsedSymbol) {
      console.error('[subscribeOnStream] Failed to parse symbol:', symbolToParse)
      return
    }

    // 使用 WebSocket 专用的周期映射
    // 如果 WebSocket 不支持某个周期，会映射到最接近的支持周期
    const resolution_str = `${OKX_WS_RESOLUTION[resolution as keyof typeof OKX_WS_RESOLUTION]}`
    if (!resolution_str) {
      console.error('[subscribeOnStream] Invalid resolution:', resolution)
      return
    }

    // OKX 频道格式: candle + 周期，例如 "candle1m", "candle5m", "candle1H"
    // 注意：OKX 使用单数形式 "candle"，不是 "candles"
    const channelName = `candle${resolution_str}`
    console.log('[subscribeOnStream] Original resolution:', resolution, '-> WebSocket resolution:', resolution_str)
    const channelString = `${channelName}~${parsedSymbol.instId}`
    console.log('[subscribeOnStream] Channel:', channelString)

    const handler = {
      id: subscriberUID,
      callback: onRealtimeCallback
    }

    let subscriptionItem = this.channelToSubscription.get(channelString)
    if (subscriptionItem) {
      // Already subscribed to the channel, use the existing subscription
      subscriptionItem.handlers.push(handler)
      console.log('[subscribeOnStream] Added handler to existing subscription')
      return
    }

    subscriptionItem = {
      subscriberUID,
      resolution,
      lastDailyBar: lastDailyBar || {
        time: Date.now(),
        open: 0,
        high: 0,
        low: 0,
        close: 0
      },
      handlers: [handler]
    }
    this.channelToSubscription.set(channelString, subscriptionItem)
    console.log('[subscribeOnStream] Created new subscription for:', channelString)

    // 等待WebSocket连接建立后再订阅
    const subscribe = () => {
      if (this.socket.readyState === WebSocket.OPEN) {
        // OKX WebSocket 订阅消息格式
        const subscribeArgs = {
          channel: channelName,
          instId: parsedSymbol.instId
        }
        console.log('[subscribeOnStream] Subscribing with args:', subscribeArgs)
        console.log('[subscribeOnStream] Channel name:', channelName)
        console.log('[subscribeOnStream] InstId:', parsedSymbol.instId)
        console.log('[subscribeOnStream] Resolution str:', resolution_str)
        this.emit('subscribe', subscribeArgs)
        console.log('[subscribeOnStream] Sent SUBSCRIBE request for:', channelString)
      } else if (this.socket.readyState === WebSocket.CONNECTING) {
        // 如果正在连接，等待连接建立
        this.socket.addEventListener('open', subscribe, { once: true })
        console.log('[subscribeOnStream] Waiting for connection to open...')
      } else {
        // 如果连接已关闭，重新创建连接
        console.log('[subscribeOnStream] Connection closed, recreating...')
        this._createSocket()
        this.socket.addEventListener('open', subscribe, { once: true })
      }
    }

    subscribe()
  }

  public unsubscribeFromStream(subscriberUID: string) {
    for (const channelString of this.channelToSubscription.keys()) {
      const subscriptionItem = this.channelToSubscription.get(channelString)
      const handlerIndex = subscriptionItem.handlers.findIndex(
        (handler: { id: string }) => handler.id === subscriberUID
      )

      if (handlerIndex !== -1) {
        // Remove from handlers
        subscriptionItem.handlers.splice(handlerIndex, 1)

        if (subscriptionItem.handlers.length === 0) {
          // Unsubscribe from the channel if it is the last handler
          console.log('[unsubscribeBars]: Unsubscribe from streaming. Channel:', channelString)

          const [channel, instId] = channelString.split('~')
          this.emit('unsubscribe', {
            channel,
            instId
          })
          this.channelToSubscription.delete(channelString)
          break
        }
      }
    }
  }

  emit(method: string, args: any) {
    if (this.socket.readyState !== WebSocket.OPEN) {
      console.log(
        `[socket] Socket is not open, cannot ${method}, this.socket.readyState = ${this.socket.readyState}`
      )
      return
    } else {
      // OKX WebSocket 消息格式: { op: "subscribe", args: [{ channel: "...", instId: "..." }] }
      const message = {
        op: method,
        args: Array.isArray(args) ? args : [args]
      }
      this.socket.send(JSON.stringify(message))
      console.log(`[socket] Sent ${method} message:`, message)
    }
  }

  private getNextDailyBarTime(barTime: number) {
    const date = new Date(barTime)
    date.setDate(date.getDate() + 1)
    return date.getTime()
  }
}
