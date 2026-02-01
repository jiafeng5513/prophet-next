import { parseFullSymbol } from './helpers'

export const BINANCE_RESOLUSION = {
  1: '1m',
  3: '3m',
  5: '5m',
  15: '15m',
  60: '1h',
  120: '2h',
  240: '4h',
  360: '6h',
  720: '12h',
  '1D': '1d',
  '2D': '2d',
  '3D': '3d',
  '1W': '1w',
  '1M': '1M'
}
export default class SocketClient {
  socket!: WebSocket
  channelToSubscription!: Map<string, any>

  constructor() {
    console.log('[SocketClient] init')
    this._createSocket()
  }

  _createSocket() {
    console.log('[SocketClient] _createSocket')
    // 使用官方推荐的端点，支持订阅/取消订阅
    this.socket = new WebSocket('wss://stream.binance.com:9443/ws')
    this.channelToSubscription = new Map()

    this.socket.onopen = () => {
      console.log('[socket] Connected to Binance WebSocket')
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

        // 处理ping帧 - 根据文档，服务器每20秒发送ping，需要回复pong
        if (data.ping) {
          this.socket.send(JSON.stringify({ pong: data.ping }))
          console.log('[socket] Sent pong response')
          return
        }

        // 处理订阅响应
        if (data.id !== undefined && data.result !== undefined) {
          console.log('[socket] Subscription response:', data)
          return
        }

        // 处理K线数据
        // 数据格式可能是直接的kline对象，或者包装在stream对象中
        let klineData = data
        if (data.stream && data.data) {
          // 组合流格式
          klineData = data.data
        }

        if (klineData.e === 'kline' && klineData.k) {
          const kline = klineData.k
          const eventTime = klineData.E

          const channelString = `${kline.s.toLowerCase()}@kline_${kline.i}`
          const subscriptionItem = this.channelToSubscription.get(channelString)

          if (!subscriptionItem || !subscriptionItem.lastDailyBar) {
            console.log('[socket] No subscription found for', channelString)
            return
          }

          const lastDailyBar = subscriptionItem.lastDailyBar
          const barStartTime = parseInt(kline.t)
          const barEndTime = parseInt(kline.T)
          const isBarClosed = kline.x // 是否完结

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
              open: parseFloat(kline.o),
              high: parseFloat(kline.h),
              low: parseFloat(kline.l),
              close: parseFloat(kline.c),
              volume: parseFloat(kline.v)
            }
            console.log('[socket] New bar closed:', bar)
            subscriptionItem.lastDailyBar = bar
          } else {
            // K线还在更新中，更新当前bar
            bar = {
              time: barStartTime,
              open: parseFloat(kline.o),
              high: parseFloat(kline.h),
              low: parseFloat(kline.l),
              close: parseFloat(kline.c),
              volume: parseFloat(kline.v)
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

    const resolution_str = `${BINANCE_RESOLUSION[resolution as keyof typeof BINANCE_RESOLUSION]}`
    if (!resolution_str) {
      console.error('[subscribeOnStream] Invalid resolution:', resolution)
      return
    }

    const channelString = `${parsedSymbol.symbol.toLowerCase()}@kline_${resolution_str}`
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
        this.emit('SUBSCRIBE', [channelString], Date.now())
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

          this.emit('UNSUBSCRIBE', [channelString], 2)
          this.channelToSubscription.delete(channelString)
          break
        }
      }
    }
  }

  emit(method: string, params: any, id: number) {
    if (this.socket.readyState !== WebSocket.OPEN) {
      console.log(
        `[socket] Socket is not open, cannot subscribe, this.socket.readyState = ${this.socket.readyState}`
      )
      return
    } else {
      this.socket.send(
        JSON.stringify({
          method,
          params,
          id
        })
      )
    }
  }

  private getNextDailyBarTime(barTime: number) {
    const date = new Date(barTime)
    date.setDate(date.getDate() + 1)
    return date.getTime()
  }
}
