/**
 * ===================================
 * 统一 TradingView DataFeed (Unified DataFeed)
 * ===================================
 *
 * 实现 TradingView Charting Library 的 IExternalDatafeed + IDatafeedChartApi 接口，
 * 通过后端 Market Data Gateway 获取 A 股 / ETF 等非虚拟货币市场的 K 线数据。
 *
 * 参考模板: binance/datafeed.ts
 */

/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
/// <reference types="@tradingview/advanced_charts/charting_library/datafeed-api" />

import {
  getKLineData,
  searchSymbols as apiSearchSymbols,
  getSymbols,
  guessMarketType,
  type SymbolInfo as ApiSymbolInfo,
} from '../../marketDataService'
import { realtimeWS } from '../../realtimeWSClient'
import type { RealtimeQuote } from '../../marketDataService'

// ==================== 周期映射 ====================

/** TradingView resolution -> 后端 period */
const RESOLUTION_MAP: Record<string, string> = {
  '1': '1',
  '5': '5',
  '15': '15',
  '30': '30',
  '60': '1h',
  '120': '2h',
  '240': '4h',
  '1D': '1d',
  '1W': '1w',
  '1M': '1M',
}

/** 根据市场类型返回交易时段 */
function getSession(marketType: string): string {
  if (marketType === 'crypto') return '24x7'
  if (marketType === 'us_stock') return '0930-1600'
  if (marketType === 'hk_stock') return '0930-1200,1300-1600'
  // A 股 / ETF: 9:30-11:30, 13:00-15:00 (不含夜盘)
  return '0930-1130,1300-1500'
}

/** 根据市场类型返回时区 */
function getTimezone(marketType: string): string {
  if (marketType === 'crypto') return 'Etc/UTC'
  if (marketType === 'us_stock') return 'America/New_York'
  if (marketType === 'hk_stock') return 'Asia/Hong_Kong'
  return 'Asia/Shanghai'
}

/** 交易所显示名 */
function getExchangeName(exchange: string): string {
  const map: Record<string, string> = {
    SSE: '上海证券交易所',
    SZSE: '深圳证券交易所',
    BSE: '北京证券交易所',
    HKEX: '香港交易所',
    HK: '香港交易所',
    NYSE: '纽约证券交易所',
    NASDAQ: '纳斯达克',
    US: '美国市场',
  }
  return map[exchange] || exchange
}

/** pricescale: 价格精度 */
function getPriceScale(marketType: string): number {
  if (marketType === 'us_stock') return 100
  if (marketType === 'hk_stock') return 1000  // 港股支持 0.001
  return 100
}

// ==================== 配置 ====================

const configurationData: TradingView.DatafeedConfiguration = {
  supported_resolutions: [
    '5', '15', '30', '60', '1D', '1W', '1M'
  ] as TradingView.ResolutionString[],
  exchanges: [
    { value: 'SSE', name: '上交所', desc: '上海证券交易所' },
    { value: 'SZSE', name: '深交所', desc: '深圳证券交易所' },
    { value: 'BSE', name: '北交所', desc: '北京证券交易所' },
    { value: 'HKEX', name: '港交所', desc: '香港交易所' },
    { value: 'NYSE', name: 'NYSE', desc: 'New York Stock Exchange' },
    { value: 'NASDAQ', name: 'NASDAQ', desc: 'NASDAQ' },
  ],
  symbols_types: [
    { name: 'A股', value: 'cn_stock' },
    { name: 'ETF', value: 'cn_etf' },
    { name: '港股', value: 'hk_stock' },
    { name: '美股', value: 'us_stock' },
  ],
  supports_marks: false,
  supports_timescale_marks: false,
  supports_time: true,
}

// ==================== DataFeed 类 ====================

export interface UnifiedDataFeedOptions {
  /** 初始标的信息 (从标的浏览器传入) */
  symbolInfo?: {
    symbol: string
    name: string
    market_type: string
    exchange: string
    data_source: string
  }
}

export default class UnifiedDataFeed
  implements TradingView.IExternalDatafeed, TradingView.IDatafeedChartApi
{
  private lastBarsCache: Map<string, TradingView.Bar> = new Map()
  private symbolInfoMap: Map<string, ApiSymbolInfo> = new Map()
  private subscribers: Map<string, { code: string; resolution: TradingView.ResolutionString; onRealtimeCallback: TradingView.SubscribeBarsCallback; onResetCacheNeededCallback: () => void }> = new Map()
  private initSymbol: UnifiedDataFeedOptions['symbolInfo']

  constructor(options?: UnifiedDataFeedOptions) {
    this.initSymbol = options?.symbolInfo
  }

  // ==================== onReady ====================

  public async onReady(callback: TradingView.OnReadyCallback): Promise<void> {
    console.log('[UnifiedDataFeed] onReady')
    setTimeout(() => callback(configurationData))
  }

  // ==================== searchSymbols ====================

  public async searchSymbols(
    userInput: string,
    exchange: string,
    symbolType: string,
    onResultReadyCallback: TradingView.SearchSymbolsCallback
  ): Promise<void> {
    console.log('[UnifiedDataFeed] searchSymbols:', userInput, exchange, symbolType)
    try {
      const results = await apiSearchSymbols(userInput, symbolType || '')
      const mapped = results.map((s) => ({
        symbol: s.symbol,
        full_name: `${s.exchange}:${s.symbol}`,
        description: s.name,
        exchange: s.exchange,
        type: s.market_type,
        ticker: `${s.exchange}:${s.symbol}`,
      }))
      onResultReadyCallback(mapped)
    } catch (err) {
      console.error('[UnifiedDataFeed] searchSymbols error:', err)
      onResultReadyCallback([])
    }
  }

  // ==================== resolveSymbol ====================

  public async resolveSymbol(
    symbolName: string,
    onSymbolResolvedCallback: TradingView.ResolveCallback,
    onResolveErrorCallback: TradingView.DatafeedErrorCallback,
    extension?: TradingView.SymbolResolveExtension
  ): Promise<void> {
    console.log('[UnifiedDataFeed] resolveSymbol:', symbolName)

    // 解析 symbolName: 可能是 "SSE:600519" 或 "600519"
    let code = symbolName
    let exchange = ''
    if (symbolName.includes(':')) {
      const parts = symbolName.split(':')
      exchange = parts[0]
      code = parts[1]
    }

    // 优先使用初始化时传入的 symbolInfo
    let info: ApiSymbolInfo | undefined
    if (this.initSymbol && this.initSymbol.symbol === code) {
      info = {
        symbol: this.initSymbol.symbol,
        name: this.initSymbol.name,
        market_type: this.initSymbol.market_type,
        exchange: this.initSymbol.exchange,
        data_source: this.initSymbol.data_source,
        base_currency: 'CNY',
        status: 'trading',
      }
    }

    // 从缓存查找
    if (!info) {
      info = this.symbolInfoMap.get(code)
    }

    // 从后端搜索
    if (!info) {
      try {
        const results = await apiSearchSymbols(code)
        if (results.length > 0) {
          // 精确匹配 symbol
          info = results.find((r) => r.symbol === code) || results[0]
        }
      } catch (err) {
        console.error('[UnifiedDataFeed] resolveSymbol search error:', err)
      }
    }

    if (!info) {
      // 最后 fallback: 猜测
      const marketType = guessMarketType(code)
      info = {
        symbol: code,
        name: code,
        market_type: marketType,
        exchange: exchange || (code.startsWith('6') ? 'SSE' : 'SZSE'),
        data_source: 'akshare',
        base_currency: 'CNY',
        status: 'trading',
      }
    }

    // 缓存
    this.symbolInfoMap.set(code, info)

    const symbolInfo: Partial<TradingView.LibrarySymbolInfo> = {
      ticker: `${info.exchange}:${info.symbol}`,
      name: info.symbol,
      description: info.name,
      type: info.market_type === 'cn_etf' ? 'fund' : 'stock',
      session: getSession(info.market_type),
      timezone: getTimezone(info.market_type) as TradingView.Timezone,
      exchange: info.exchange,
      listed_exchange: info.exchange,
      minmov: 1,
      pricescale: getPriceScale(info.market_type),
      has_intraday: true,
      has_daily: true,
      has_weekly_and_monthly: true,
      visible_plots_set: 'ohlcv',
      supported_resolutions: configurationData.supported_resolutions!,
      volume_precision: 0,
      data_status: 'pulsed',
    }

    console.log('[UnifiedDataFeed] Symbol resolved:', symbolInfo.ticker, symbolInfo.description)
    onSymbolResolvedCallback(symbolInfo as TradingView.LibrarySymbolInfo)
  }

  // ==================== getBars ====================

  public async getBars(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    periodParams: TradingView.PeriodParams,
    onHistoryCallback: TradingView.HistoryCallback,
    onErrorCallback: TradingView.DatafeedErrorCallback
  ): Promise<void> {
    const { from, to, firstDataRequest } = periodParams
    const code = symbolInfo.name || symbolInfo.ticker?.split(':')[1] || ''
    const period = RESOLUTION_MAP[resolution as string] || '1d'
    const marketType = this.symbolInfoMap.get(code)?.market_type || guessMarketType(code)

    console.log(
      `[UnifiedDataFeed] getBars: ${code} ${period} from ${new Date(from * 1000).toISOString()} to ${new Date(to * 1000).toISOString()}`
    )

    try {
      const { bars: rawBars, noData } = await getKLineData(code, marketType, period, from, to)

      if (noData || rawBars.length === 0) {
        console.log('[UnifiedDataFeed] getBars: no data')
        onHistoryCallback([], { noData: true })
        return
      }

      // 后端返回 Unix 秒, TradingView 需要毫秒
      const bars: TradingView.Bar[] = rawBars
        .filter((b) => b.time >= from && b.time < to)
        .map((b) => ({
          time: b.time * 1000,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
          volume: b.volume || 0,
        }))

      // 按时间排序
      bars.sort((a, b) => a.time - b.time)

      if (bars.length > 0 && firstDataRequest) {
        this.lastBarsCache.set(code, { ...bars[bars.length - 1] })
      }

      console.log(`[UnifiedDataFeed] getBars: returned ${bars.length} bar(s)`)
      onHistoryCallback(bars, { noData: bars.length === 0 })
    } catch (error) {
      console.error('[UnifiedDataFeed] getBars error:', error)
      onErrorCallback(String(error))
    }
  }

  // ==================== subscribeBars ====================

  public async subscribeBars(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    onRealtimeCallback: TradingView.SubscribeBarsCallback,
    subscriberUID: string,
    onResetCacheNeededCallback: () => void
  ): Promise<void> {
    console.log('[UnifiedDataFeed] subscribeBars:', subscriberUID)

    const code = symbolInfo.name || symbolInfo.ticker?.split(':')[1] || ''
    const period = RESOLUTION_MAP[resolution as string] || '1d'

    // 保存订阅信息
    this.subscribers.set(subscriberUID, {
      code,
      resolution,
      onRealtimeCallback,
      onResetCacheNeededCallback,
    })

    // 通过 WebSocket 订阅实时行情
    realtimeWS.subscribeQuotes(
      `datafeed-${subscriberUID}`,
      [code],
      (quotes: RealtimeQuote[]) => {
        const q = quotes.find((item) => item.symbol === code)
        if (!q || !q.price) return

        const lastBar = this.lastBarsCache.get(code)
        if (!lastBar) return

        const tradeTime = q.timestamp ? q.timestamp * 1000 : Date.now()
        const barPeriodMs = this._getBarPeriodMs(period)

        // 判断是否属于当前 bar 还是新 bar
        const currentBarStart = lastBar.time
        const nextBarStart = currentBarStart + barPeriodMs

        if (tradeTime >= nextBarStart) {
          // 新 bar
          const newBar: TradingView.Bar = {
            time: nextBarStart,
            open: q.price,
            high: q.price,
            low: q.price,
            close: q.price,
            volume: q.volume || 0,
          }
          this.lastBarsCache.set(code, newBar)
          onRealtimeCallback(newBar)
        } else {
          // 更新当前 bar
          const updatedBar: TradingView.Bar = {
            ...lastBar,
            high: Math.max(lastBar.high, q.price),
            low: Math.min(lastBar.low, q.price),
            close: q.price,
            volume: (lastBar.volume || 0) + (q.volume || 0),
          }
          this.lastBarsCache.set(code, updatedBar)
          onRealtimeCallback(updatedBar)
        }
      }
    )
  }

  // ==================== unsubscribeBars ====================

  public async unsubscribeBars(subscriberUID: string): Promise<void> {
    console.log('[UnifiedDataFeed] unsubscribeBars:', subscriberUID)
    const sub = this.subscribers.get(subscriberUID)
    if (sub) {
      realtimeWS.unsubscribeQuotes(`datafeed-${subscriberUID}`, [sub.code])
      this.subscribers.delete(subscriberUID)
    }
  }

  // ==================== 辅助: bar 周期毫秒数 ====================

  private _getBarPeriodMs(period: string): number {
    const map: Record<string, number> = {
      '1': 60_000,
      '5': 5 * 60_000,
      '15': 15 * 60_000,
      '30': 30 * 60_000,
      '1h': 60 * 60_000,
      '2h': 2 * 60 * 60_000,
      '4h': 4 * 60 * 60_000,
      '1d': 24 * 60 * 60_000,
      '1w': 7 * 24 * 60 * 60_000,
      '1M': 30 * 24 * 60 * 60_000,
    }
    return map[period] || 24 * 60 * 60_000
  }

  // ==================== getServerTime ====================

  public async getServerTime(callback: TradingView.ServerTimeCallback): Promise<void> {
    callback(Math.floor(Date.now() / 1000))
  }
}
