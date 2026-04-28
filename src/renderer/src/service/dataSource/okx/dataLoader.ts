/**
 * OKX DataLoader for KLineChart
 * 适配 KLineChart 的 setLoadDataCallback 接口，
 * 复用现有的 OKX REST API 和 WebSocket 逻辑。
 */

import { makeOKXRequest, parseFullSymbol } from './helpers'

/** OKX K线周期映射 */
const OKX_INTERVAL_MAP: Record<string, string> = {
  '1': '1m',
  '3': '3m',
  '5': '5m',
  '15': '15m',
  '30': '30m',
  '60': '1H',
  '120': '2H',
  '240': '4H',
  '360': '6H',
  '720': '12H',
  '1D': '1D',
  '2D': '2D',
  '3D': '3D',
  '1W': '1W',
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

export default class OKXDataLoader {
  private socket: WebSocket | null = null
  private currentSubscription: { channelName: string; instId: string; callback: (bar: KLineBar) => void } | null = null

  /**
   * 获取历史 K 线数据
   */
  async getBars(params: GetBarsParams): Promise<KLineBar[]> {
    const { symbol, interval, type, timestamp } = params

    const parsedSymbol = parseFullSymbol(symbol)
    if (!parsedSymbol) {
      console.error('[OKXDataLoader] Failed to parse symbol:', symbol)
      return []
    }

    const okxInterval = OKX_INTERVAL_MAP[interval]
    if (!okxInterval) {
      console.error('[OKXDataLoader] Unsupported interval:', interval)
      return []
    }

    // OKX API: instId, bar, before, after, limit
    // after: 返回时间戳早于该值的数据（ts < after）
    const urlParams: Record<string, string | number> = {
      instId: parsedSymbol.instId,
      bar: okxInterval,
      limit: 300
    }

    if (type === 'forward' && timestamp) {
      // 向左加载更早的数据
      urlParams.after = timestamp
    }

    const query = Object.keys(urlParams)
      .map((key) => `${key}=${encodeURIComponent(urlParams[key])}`)
      .join('&')

    try {
      console.log(`[OKXDataLoader] getBars type=${type}, url=api/v5/market/candles?${query}`)
      const data = await makeOKXRequest(`api/v5/market/candles?${query}`)

      if (data.code !== '0' || !data.data || data.data.length === 0) {
        return []
      }

      // OKX K线格式: [timestamp(ms), open, high, low, close, volume, ...]
      // OKX 返回数据倒序（最新在前），需要反转
      const bars: KLineBar[] = data.data
        .map((item: string[]) => ({
          timestamp: parseInt(item[0]),
          open: parseFloat(item[1]),
          high: parseFloat(item[2]),
          low: parseFloat(item[3]),
          close: parseFloat(item[4]),
          volume: parseFloat(item[5])
        }))
        .reverse()

      console.log(`[OKXDataLoader] getBars returned ${bars.length} bars`)
      return bars
    } catch (error) {
      console.error('[OKXDataLoader] getBars error:', error)
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
      console.error('[OKXDataLoader] subscribe: Failed to parse symbol:', symbol)
      return
    }

    const okxInterval = OKX_INTERVAL_MAP[interval]
    if (!okxInterval) {
      console.error('[OKXDataLoader] subscribe: Unsupported interval:', interval)
      return
    }

    // OKX 频道格式: candle + 周期, 如 "candle1m", "candle5m", "candle1H"
    const channelName = `candle${okxInterval}`
    console.log('[OKXDataLoader] subscribing to:', channelName, parsedSymbol.instId)

    // 先取消之前的订阅
    this.unsubscribe()

    this.currentSubscription = { channelName, instId: parsedSymbol.instId, callback }

    // 创建 WebSocket 连接
    this._ensureSocket()

    const doSubscribe = () => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({
          op: 'subscribe',
          args: [{
            channel: channelName,
            instId: parsedSymbol.instId
          }]
        }))
        console.log('[OKXDataLoader] subscribe sent')
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
        op: 'unsubscribe',
        args: [{
          channel: this.currentSubscription.channelName,
          instId: this.currentSubscription.instId
        }]
      }))
      console.log('[OKXDataLoader] unsubscribe sent')
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

    this.socket = new WebSocket('wss://ws.okx.com:8443/ws/v5/public')

    this.socket.onopen = () => {
      console.log('[OKXDataLoader] WebSocket connected')
    }

    this.socket.onclose = (event) => {
      console.log('[OKXDataLoader] WebSocket disconnected:', event.code, event.reason)
    }

    this.socket.onerror = (error) => {
      console.error('[OKXDataLoader] WebSocket error:', error)
    }

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // 处理订阅/取消订阅确认
        if (data.event) {
          if (data.event === 'error') {
            console.error('[OKXDataLoader] WS error:', data.code, data.msg)
          }
          return
        }

        // 处理 K 线数据
        // 格式: { arg: { channel: "candle1m", instId: "BTC-USDT" }, data: [[ts, o, h, l, c, vol, ...]] }
        if (data.arg && data.arg.channel && data.arg.channel.startsWith('candle') && data.data && this.currentSubscription) {
          const klineData = data.data[0]
          if (!klineData || klineData.length < 6) return

          const bar: KLineBar = {
            timestamp: parseInt(klineData[0]),
            open: parseFloat(klineData[1]),
            high: parseFloat(klineData[2]),
            low: parseFloat(klineData[3]),
            close: parseFloat(klineData[4]),
            volume: parseFloat(klineData[5])
          }
          this.currentSubscription.callback(bar)
        }
      } catch (error) {
        console.error('[OKXDataLoader] message parse error:', error)
      }
    }
  }
}
