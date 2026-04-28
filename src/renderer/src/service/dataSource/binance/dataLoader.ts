/**
 * Binance DataLoader for KLineChart
 * 适配 KLineChart 的 setLoadDataCallback 接口，
 * 复用现有的 Binance REST API 和 WebSocket 逻辑。
 */

import { makeBinanceRequest, parseFullSymbol } from './helpers'

/** Binance K线周期映射 */
const BINANCE_INTERVAL_MAP: Record<string, string> = {
  '1': '1m',
  '3': '3m',
  '5': '5m',
  '15': '15m',
  '60': '1h',
  '120': '2h',
  '240': '4h',
  '360': '6h',
  '720': '12h',
  '1D': '1d',
  '2D': '2d',
  '3D': '3d',
  '1W': '1w',
  '1M': '1M'
}

interface GetBarsParams {
  symbol: string
  exchange: string
  interval: string
  type: 'init' | 'forward'
  timestamp?: number
}

interface SubscribeParams {
  symbol: string
  exchange: string
  interval: string
  callback: (bar: KLineBar) => void
}

interface KLineBar {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export default class BinanceDataLoader {
  private socket: WebSocket | null = null
  private channelToSubscription: Map<string, any> = new Map()
  private currentSubscription: { channel: string; callback: (bar: KLineBar) => void } | null = null

  /**
   * 获取历史 K 线数据
   */
  async getBars(params: GetBarsParams): Promise<KLineBar[]> {
    const { symbol, interval, type, timestamp } = params

    const parsedSymbol = parseFullSymbol(symbol)
    if (!parsedSymbol) {
      console.error('[BinanceDataLoader] Failed to parse symbol:', symbol)
      return []
    }

    const binanceInterval = BINANCE_INTERVAL_MAP[interval]
    if (!binanceInterval) {
      console.error('[BinanceDataLoader] Unsupported interval:', interval)
      return []
    }

    const urlParams: Record<string, string | number> = {
      symbol: parsedSymbol.symbol,
      interval: binanceInterval,
      limit: 500
    }

    if (type === 'forward' && timestamp) {
      // 向左加载更早的数据：endTime 设为当前最左侧 bar 的时间戳
      urlParams.endTime = timestamp
    }

    const query = Object.keys(urlParams)
      .map((key) => `${key}=${encodeURIComponent(urlParams[key])}`)
      .join('&')

    try {
      console.log(`[BinanceDataLoader] getBars type=${type}, url=api/v3/klines?${query}`)
      const data = await makeBinanceRequest(`api/v3/klines?${query}`)

      if (!data || data.length === 0) {
        return []
      }

      // Binance K线格式: [timestamp(ms), open, high, low, close, volume, ...]
      const bars: KLineBar[] = data.map((item: any[]) => ({
        timestamp: parseInt(item[0]),
        open: parseFloat(item[1]),
        high: parseFloat(item[2]),
        low: parseFloat(item[3]),
        close: parseFloat(item[4]),
        volume: parseFloat(item[5])
      }))

      // 按时间升序排列
      bars.sort((a, b) => a.timestamp - b.timestamp)

      console.log(`[BinanceDataLoader] getBars returned ${bars.length} bars`)
      return bars
    } catch (error) {
      console.error('[BinanceDataLoader] getBars error:', error)
      return []
    }
  }

  /**
   * 订阅实时 K 线推送
   */
  subscribe(params: SubscribeParams): void {
    const { symbol, interval, callback } = params

    const parsedSymbol = parseFullSymbol(symbol)
    if (!parsedSymbol) {
      console.error('[BinanceDataLoader] subscribe: Failed to parse symbol:', symbol)
      return
    }

    const binanceInterval = BINANCE_INTERVAL_MAP[interval]
    if (!binanceInterval) {
      console.error('[BinanceDataLoader] subscribe: Unsupported interval:', interval)
      return
    }

    const channel = `${parsedSymbol.symbol.toLowerCase()}@kline_${binanceInterval}`
    console.log('[BinanceDataLoader] subscribing to:', channel)

    // 先取消之前的订阅
    this.unsubscribe()

    this.currentSubscription = { channel, callback }

    // 创建 WebSocket 连接
    this._ensureSocket()

    const doSubscribe = () => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({
          method: 'SUBSCRIBE',
          params: [channel],
          id: Date.now()
        }))
        console.log('[BinanceDataLoader] SUBSCRIBE sent for:', channel)
      }
    }

    if (this.socket!.readyState === WebSocket.OPEN) {
      doSubscribe()
    } else {
      this.socket!.addEventListener('open', doSubscribe, { once: true })
    }
  }

  /**
   * 取消订阅
   */
  unsubscribe(): void {
    if (this.currentSubscription && this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        method: 'UNSUBSCRIBE',
        params: [this.currentSubscription.channel],
        id: Date.now()
      }))
      console.log('[BinanceDataLoader] UNSUBSCRIBE sent for:', this.currentSubscription.channel)
    }
    this.currentSubscription = null
  }

  /**
   * 完全销毁，关闭 WebSocket
   */
  destroy(): void {
    this.unsubscribe()
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  private _ensureSocket(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.socket = new WebSocket('wss://stream.binance.com:9443/ws')

    this.socket.onopen = () => {
      console.log('[BinanceDataLoader] WebSocket connected')
    }

    this.socket.onclose = (event) => {
      console.log('[BinanceDataLoader] WebSocket disconnected:', event.code, event.reason)
    }

    this.socket.onerror = (error) => {
      console.error('[BinanceDataLoader] WebSocket error:', error)
    }

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // 回复 ping
        if (data.ping) {
          this.socket!.send(JSON.stringify({ pong: data.ping }))
          return
        }

        // 忽略订阅确认
        if (data.id !== undefined && data.result !== undefined) {
          return
        }

        // 处理 K 线数据
        let klineData = data
        if (data.stream && data.data) {
          klineData = data.data
        }

        if (klineData.e === 'kline' && klineData.k && this.currentSubscription) {
          const k = klineData.k
          const bar: KLineBar = {
            timestamp: parseInt(k.t),
            open: parseFloat(k.o),
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: parseFloat(k.c),
            volume: parseFloat(k.v)
          }
          this.currentSubscription.callback(bar)
        }
      } catch (error) {
        console.error('[BinanceDataLoader] message parse error:', error)
      }
    }
  }
}
