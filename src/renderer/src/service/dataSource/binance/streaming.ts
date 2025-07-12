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
    this.socket = new WebSocket('wss://data-stream.binance.vision/ws')
    // this.socket = new WebSocket('wss://data-stream.binance.vision/ws')
    //
    this.channelToSubscription = new Map()

    this.socket.addEventListener('connect', () => {
      console.log('[socket] Connected')
    })

    this.socket.addEventListener('disconnect', (reason: any) => {
      console.log('[socket] Disconnected:', reason)
    })

    this.socket.addEventListener('error', (error: any) => {
      console.log('[socket] Error:', error)
    })

    this.socket.addEventListener('message', ({ data }) => {
      console.log("[socket] Message:", data);
      /**
        {
          "e": "kline",          // 事件类型
          "E": 1672515782136,    // 事件时间
          "s": "BNBBTC",         // 交易对
          "k": {
            "t": 1672515780000,  // 这根K线的起始时间
            "T": 1672515839999,  // 这根K线的结束时间
            "s": "BNBBTC",       // 交易对
            "i": "1m",           // K线间隔
            "f": 100,            // 这根K线期间第一笔成交ID
            "L": 200,            // 这根K线期间末一笔成交ID
            "o": "0.0010",       // 这根K线期间第一笔成交价
            "c": "0.0020",       // 这根K线期间末一笔成交价
            "h": "0.0025",       // 这根K线期间最高成交价
            "l": "0.0015",       // 这根K线期间最低成交价
            "v": "1000",         // 这根K线期间成交量
            "n": 100,            // 这根K线期间成交数量
            "x": false,          // 这根K线是否完结（是否已经开始下一根K线）
            "q": "1.0000",       // 这根K线期间成交额
            "V": "500",          // 主动买入的成交量
            "Q": "0.500",        // 主动买入的成交额
            "B": "123456"        // 忽略此参数
          }
        } */
      const { E: time, k: kline } = JSON.parse(data)

      if (!kline) {
        // Skip all non-trading events
        return
      }
      const tradePrice = parseFloat(kline.c)
      const tradeTime = parseInt(time)
      const thisBarStartTime = parseInt(kline.t)
      const thisBarEndTime = parseInt(kline.T)
      const barDelatTime = thisBarEndTime - thisBarStartTime + 1

      const channelString = `${kline.s.toLowerCase()}@kline_${kline.i}`
      const subscriptionItem = this.channelToSubscription.get(channelString)
      console.log('[subscriptionItem]', subscriptionItem)
      if (subscriptionItem === undefined) {
        return
      }
      const lastDailyBar = subscriptionItem.lastDailyBar
      // 这里应该根据当前的时间分辨率计算新bar生成的时机
      const nextDailyBarTime = lastDailyBar.time + barDelatTime

      let bar: {
        time: number
        open: number
        high: number
        low: number
        close: number
      }
      if (tradeTime > thisBarEndTime) {
        bar = {
          time: nextDailyBarTime,
          open: tradePrice,
          high: tradePrice,
          low: tradePrice,
          close: tradePrice
        }
        console.log('[socket] Generate new bar', bar)
      } else {
        bar = {
          ...lastDailyBar,
          high: Math.max(lastDailyBar.high, tradePrice),
          low: Math.min(lastDailyBar.low, tradePrice),
          close: tradePrice
        }
        console.log('[socket] Update the latest bar by', bar)
      }

      subscriptionItem.lastDailyBar = bar

      // Send data to every subscriber of that symbol
      subscriptionItem.handlers.forEach((handler: { callback: (arg0: any) => any }) =>
        handler.callback(bar)
      )
    })
  }

  public subscribeOnStream(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    onRealtimeCallback: TradingView.SubscribeBarsCallback,
    subscriberUID: string,
    onResetCacheNeededCallback: () => void,
    lastDailyBar: TradingView.Bar | undefined
  ) {
    const parsedSymbol = parseFullSymbol(symbolInfo.full_name)
    if (parsedSymbol) {
      const resolution_str = `${BINANCE_RESOLUSION[resolution as keyof typeof BINANCE_RESOLUSION]}`
      const channelString = `${parsedSymbol.symbol.toLowerCase()}@kline_${resolution_str}`

      const handler = {
        id: subscriberUID,
        callback: onRealtimeCallback
      }
      let subscriptionItem = this.channelToSubscription.get(channelString)
      if (subscriptionItem) {
        // Already subscribed to the channel, use the existing subscription
        subscriptionItem.handlers.push(handler)
        return
      }
      subscriptionItem = {
        subscriberUID,
        resolution,
        lastDailyBar,
        handlers: [handler]
      }
      this.channelToSubscription.set(channelString, subscriptionItem)
      console.log('[subscribeBars]: Subscribe to streaming. Channel:', channelString)

      this.emit('SUBSCRIBE', [channelString], 1)
    }
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
