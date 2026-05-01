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
  // A 股 / ETF: 9:30-11:30, 13:00-15:00 (不含夜盘)
  return '0930-1130,1300-1500'
}

/** 根据市场类型返回时区 */
function getTimezone(marketType: string): string {
  if (marketType === 'crypto') return 'Etc/UTC'
  return 'Asia/Shanghai'
}

/** 交易所显示名 */
function getExchangeName(exchange: string): string {
  const map: Record<string, string> = {
    SSE: '上海证券交易所',
    SZSE: '深圳证券交易所',
    BSE: '北京证券交易所',
  }
  return map[exchange] || exchange
}

/** pricescale: A 股价格精度 0.01 -> pricescale 100 */
function getPriceScale(marketType: string): number {
  if (marketType === 'cn_stock' || marketType === 'cn_etf') return 100
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
  ],
  symbols_types: [
    { name: 'A股', value: 'cn_stock' },
    { name: 'ETF', value: 'cn_etf' },
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
    // A 股 / ETF 暂不支持实时推送 (后续可通过轮询或 TickFlow WS 实现)
    // 这里留空，图表将只显示历史数据
  }

  // ==================== unsubscribeBars ====================

  public async unsubscribeBars(subscriberUID: string): Promise<void> {
    console.log('[UnifiedDataFeed] unsubscribeBars:', subscriberUID)
  }

  // ==================== getServerTime ====================

  public async getServerTime(callback: TradingView.ServerTimeCallback): Promise<void> {
    callback(Math.floor(Date.now() / 1000))
  }
}
