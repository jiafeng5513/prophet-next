/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
/// <reference types="@tradingview/trading_platform/charting_library/datafeed-api" />
import { generateSymbol, makeApiRequest, makeBinanceRequest, parseFullSymbol, priceScale } from './helpers'
import SocketClient, { BINANCE_RESOLUSION } from './streaming'

const configurationData: TradingView.DatafeedConfiguration = {
  // Represents the resolutions for bars supported by your datafeed
  supported_resolutions: [
    '5',
    '15',
    '1H',
    '4H',
    '1D',
    '3D',
    '1W',
    '1M'
  ] as TradingView.ResolutionString[],
  // The `exchanges` arguments are used for the `searchSymbols` method if a user selects the exchange
  exchanges: [{ value: 'Binance', name: 'Binance', desc: 'Binance' }],
  // The `symbols_types` arguments are used for the `searchSymbols` method if a user selects this symbol type
  symbols_types: [{ name: 'crypto', value: 'crypto' }],
  // currency_codes: [“USD”，“EUR”，“GBP”] 用于货币转换的支持的货币数组
  // units列出支持的单位组的对象。 每个组可以有多个单位对象。 每个单位对象应具有以下字段：
  //    id: string.唯一主键
  //    name: string.缩略名
  //    description: string.简介
  //    例如:
  //    {
  //      weight: [
  //        { id: 'kg', name: 'kg', description: 'Kilograms' },
  //        { id: 'lb', name: 'lb', description: 'Pounds' },
  //      ]
  //    }
  supports_marks: true, // 布尔值来标识您的 datafeed 是否支持在K线上显示标记。
  supports_timescale_marks: true, //布尔值来标识您的 datafeed 是否支持时间刻度标记。
  supports_time: true //将此设置为true假如您的datafeed提供服务器时间（unix时间）。 它仅用于在价格刻度上显示倒计时。
  // symbols_grouping: 如果要在商品搜索中对商品进行分组，请设置它。 值为一个对象，其中键是商品类型，值是正则表达式（每个正则表达式应该将一个期货名称分为两部分：合约种类和到期时间）。
  //   例如
  //     {
  //       "futures": `/^(.+)([12]!|[FGHJKMNQUVXZ]\d{1,2})$/`,
  //       "stock": `/^(.+)([12]!|[FGHJKMNQUVXZ]\d{1,2})$/`,
  //     }
}

export interface DataFeedOptions {
  SymbolInfo?: TradingView.LibrarySymbolInfo
  DatafeedConfiguration?: TradingView.DatafeedConfiguration
  getBars?: TradingView.IDatafeedChartApi['getBars']
}

export default class DataFeed
  implements TradingView.IExternalDatafeed, TradingView.IDatafeedChartApi
{
  private options: DataFeedOptions
  private lastBarsCache: Map<string, TradingView.Bar>
  private socket!: SocketClient

  constructor(options?: DataFeedOptions) {
    this.lastBarsCache = new Map()
    if (!options) {
      this.options = { DatafeedConfiguration: configurationData }
    } else {
      this.options = options
    }
  }

  /**
   * jsAPI
   * 此方法可以设置图表库支持的图表配置。这些数据会影响到图表支持的功能，所以它被称为服务端定制。
   * 图表库要求您使用回调函数来传递datafeed的 configurationData参数。
   * @param callback configurationData 是一个对象，现在支持以下属性
   */
  public async onReady(callback: TradingView.OnReadyCallback) {
    console.log('[onReady]: Method call')
    setTimeout(() => callback(configurationData))
    this.socket = new SocketClient()
  }

  /**
   * jsAPI
   * @param userInput  : string，用户在商品搜索框中输入的文字。
   * @param exchange   : string，请求的交易所（由用户选择）。空值表示没有指定。
   * @param symbolType :  string，请求的商品类型：index、stock、forex等等（由用户选择）。空值表示没有指定。
   * @param onResultReadyCallback : function(result), results是一个json数组
   */
  public async searchSymbols(
    userInput: string,
    exchange: string,
    symbolType: string,
    onResultReadyCallback: TradingView.SearchSymbolsCallback
  ) {
    console.log('[searchSymbols]: Method call')
    const symbols = await this.getAllSymbols()
    const newSymbols = symbols.filter((symbol) => {
      const isExchangeValid = exchange === '' || symbol.exchange === exchange
      const isFullSymbolContainsInput =
        symbol.full_name.toLowerCase().indexOf(userInput.toLowerCase()) !== -1
      return isExchangeValid && isFullSymbolContainsInput
    })
    onResultReadyCallback(newSymbols)
  }

  private async getAllSymbols() {
    console.log('[getAllSymbols]: Method call')
    const data = await makeBinanceRequest('api/v3/exchangeInfo')

    let allSymbols: any[] = []

    for (const exchange of configurationData.exchanges!) {
      const pairs = data.symbols

      for (const pair of pairs) {
        const symbolInfo = generateSymbol(exchange.value, pair.baseAsset, pair.quoteAsset)
        // console.log(`[getAllSymbols]: symbolInfo.short = ${symbolInfo.short}`)
        const symbol = {
          symbol: symbolInfo.short,
          full_name: symbolInfo.full,
          description: symbolInfo.short,
          exchange: exchange.value,
          type: 'crypto',
          tickSize: pair.filters[0].tickSize
        }
        allSymbols = [...allSymbols, symbol]
      }
    }

    return allSymbols
  }
  /**
   * jsAPI
   * 通过商品名称解析商品信息
   * @param symbolName : string，商品名称 或ticker
   * @param onSymbolResolvedCallback : function(SymbolInfo)
   * @param onResolveErrorCallback : function(reason)
   * @param extension : 具有附加参数的可选对象。 它具有以下字段：
   *        currencyCode: string, 如果设置了currency_codes配置字段并且在原始商品信息中提供了currency_code，则可以提供它来表示要转换的货币。
   *        unitId: string. 如果 units 配置，它可以被提供来指示要转换的单位。 设置字段并在商品信息中提供 unit_id 。
   * @returns
   */
  public async resolveSymbol(
    symbolName: string,
    onSymbolResolvedCallback: TradingView.ResolveCallback,
    onResolveErrorCallback: TradingView.DatafeedErrorCallback,
    extension: TradingView.SymbolResolveExtension
  ) {
    console.log('[resolveSymbol]: Resolving symbol:', symbolName)
    const symbols = await this.getAllSymbols()
    
    // 首先尝试精确匹配
    let symbolItem = symbols.find(({ full_name }) => full_name === symbolName)
    
    // 如果找不到，尝试规范化 symbolName
    if (!symbolItem) {
      // 如果 symbolName 不包含 ":"，尝试添加 "Binance:" 前缀
      if (!symbolName.includes(':')) {
        const normalizedName = `Binance:${symbolName}`
        console.log('[resolveSymbol]: Trying normalized name:', normalizedName)
        symbolItem = symbols.find(({ full_name }) => full_name === normalizedName)
      }
      
      // 如果还是找不到，尝试通过 symbol (short name) 匹配
      if (!symbolItem) {
        console.log('[resolveSymbol]: Trying to match by short name:', symbolName)
        symbolItem = symbols.find(({ symbol }) => symbol === symbolName)
      }
    }
    
    if (!symbolItem) {
      console.error('[resolveSymbol]: Cannot resolve symbol', symbolName)
      onResolveErrorCallback(`Cannot resolve symbol: ${symbolName}`)
      return
    }
    
    // Symbol information object
    const symbolInfo: Partial<TradingView.LibrarySymbolInfo> = {
      ticker: symbolItem.full_name, // 始终使用完整格式 "Binance:BTC/USDT"
      name: symbolItem.symbol, // 短名称 "BTC/USDT"
      description: symbolItem.description,
      type: symbolItem.type,
      session: '24x7',
      timezone: 'Etc/UTC',
      exchange: symbolItem.exchange,
      minmov: 1,
      pricescale: priceScale(symbolItem.tickSize),
      has_intraday: true,
      has_daily: true,
      has_weekly_and_monthly: false,
      visible_plots_set: 'ohlcv',
      supported_resolutions: configurationData.supported_resolutions!,
      volume_precision: 2,
      data_status: 'streaming'
    }
    console.log('[resolveSymbol]: Symbol resolved successfully:', symbolItem.full_name)
    onSymbolResolvedCallback(symbolInfo as TradingView.LibrarySymbolInfo)
  }

  /**
   * jsAPI
   * 当图表库需要由日期范围定义的历史K线片段时，将调用此函数。
   * @param symbolInfo SymbolInfo 商品信息对象
   * @param resolution : string （周期）
   * @param periodParams : 具有以下字段的对象:
   *    from - unix 时间戳, 最左边请求的K线时间(K线时间 >= from)
   *    countBack - 要加载的K线的确切数量，如果您的datafeed支持它（见下文），则将视为拥有比 from 更高的优先级。 如果用户请求特定时间段，则可以不指定。
   *    to: unix 时间戳, 最右边请求的K线时间(K线时间 < to)
   *    firstDataRequest: 布尔值，以标识是否第一次调用此商品/周期的历史记录。当设置为true时 你可以忽略to参数（这取决于浏览器的Date.now()) 并返回K线数组直到最新K线。
   * @param onHistoryCallback : function(数组bars,meta={ noData = false }) 历史数据的回调函数。每次请求只应被调用一次。 此函数有2个参数：
   *    bars: Bar对象数组{time, close, open, high, low, volume}[]
   *    meta: object{noData = true | false, nextTime = unix time}
   * @param onErrorCallback :function(reason：错误原因) 错误的回调函数。 此函数的唯一参数是文本错误消息。
   * @returns
   */
  public async getBars(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    periodParams: TradingView.PeriodParams,
    onHistoryCallback: TradingView.HistoryCallback,
    onErrorCallback: TradingView.DatafeedErrorCallback
  ) {
    console.log(
      `[getBars]: Method call ${symbolInfo.name} from ${periodParams.from} to ${periodParams.to}`
    )
    const { from, to, firstDataRequest } = periodParams

    // 使用 ticker 或 name，确保能正确解析
    const symbolToParse = symbolInfo.ticker || symbolInfo.name || ''
    console.log(`[getBars]: Parsing symbol - ticker: ${symbolInfo.ticker}, name: ${symbolInfo.name}`)
    const parsedSymbol = parseFullSymbol(symbolToParse)
    console.log(`[getBars]: parsedSymbol = ${parsedSymbol}`)
    if (!parsedSymbol) {
      onErrorCallback(`Failed to parse symbol: ${symbolToParse}`)
      return
    }

    const interval = BINANCE_RESOLUSION[resolution as keyof typeof BINANCE_RESOLUSION]
    if (!interval) {
      onErrorCallback(`Unsupported resolution: ${resolution}`)
      return
    }

    // Binance API 使用毫秒时间戳，TradingView 传入的 from/to 是秒时间戳
    const urlParameters: Record<string, string | number> = {
      symbol: parsedSymbol.symbol,
      interval: interval,
      limit: 1000
    }

    // 添加时间范围参数（可选，但有助于获取准确的数据）
    if (from) {
      urlParameters.startTime = from * 1000
    }
    if (to) {
      urlParameters.endTime = to * 1000
    }

    const query = Object.keys(urlParameters)
      .map(
        (name) =>
          `${name}=${encodeURIComponent(urlParameters[name])}`
      )
      .join('&')

    try {
      console.log(`[getBars]: Requesting ${parsedSymbol.symbol} ${interval} from ${new Date(from * 1000).toISOString()} to ${new Date(to * 1000).toISOString()}`)
      console.log(`[getBars]: URL: api/v3/klines?${query}`)
      const data = await makeBinanceRequest(`api/v3/klines?${query}`)
      
      if (!data || data.length === 0) {
        console.log('[getBars]: No data returned')
        onHistoryCallback([], { noData: true })
        return
      }

      let bars: {
        time: number
        low: number
        high: number
        open: number
        close: number
        volume: number
      }[] = []

      // Binance K线数据格式: [时间戳(ms), 开盘价, 最高价, 最低价, 收盘价, 成交量, ...]
      data.forEach((bar: any[]) => {
        const barTime = parseInt(bar[0])
        // 过滤时间范围（使用毫秒比较）
        if (barTime >= from * 1000 && barTime < to * 1000) {
          bars.push({
            time: barTime, // 已经是毫秒时间戳
            open: parseFloat(bar[1]),
            high: parseFloat(bar[2]),
            low: parseFloat(bar[3]),
            close: parseFloat(bar[4]),
            volume: parseFloat(bar[5])
          })
        }
      })

      // 按时间排序（确保顺序正确）
      bars.sort((a, b) => a.time - b.time)

      if (bars.length > 0 && firstDataRequest) {
        // 保存最后一根K线用于实时更新
        this.lastBarsCache.set(symbolInfo.name, {
          ...bars[bars.length - 1]
        })
        console.log('[getBars] Cached last bar:', bars[bars.length - 1])
      }

      console.log(`[getBars]: Returned ${bars.length} bar(s)`)
      onHistoryCallback(bars, { noData: bars.length === 0 })
    } catch (error) {
      console.error('[getBars]: Error:', error)
      onErrorCallback(String(error))
    }
  }

  /**
   * jsAPI
   * 订阅K线数据。图表库将调用onRealtimeCallback方法以更新实时数据
   * @param symbolInfo :object SymbolInfo
   * @param resolution : string 周期
   * @param onRealtimeCallback : function(bar), bar is object{time, close, open, high, low, volume}
   * @param subscriberUID
   * @param onResetCacheNeededCallback : function()将在bars数据发生变化时执行
   */
  public async subscribeBars(
    symbolInfo: TradingView.LibrarySymbolInfo,
    resolution: TradingView.ResolutionString,
    onRealtimeCallback: TradingView.SubscribeBarsCallback,
    subscriberUID: string,
    onResetCacheNeededCallback: () => void
  ) {
    console.log('[subscribeBars]: Method call with subscriberUID:', subscriberUID)
    this.socket.subscribeOnStream(
      symbolInfo,
      resolution,
      onRealtimeCallback,
      subscriberUID,
      onResetCacheNeededCallback,
      this.lastBarsCache.get(symbolInfo.name)
    )
  }
  /**
   * jsAPI
   * 取消订阅K线数据。在调用subscribeBars方法时,图表库将跳过与subscriberUID相同的对象。
   * @param subscriberUID
   */
  public async unsubscribeBars(subscriberUID: string) {
    console.log('[unsubscribeBars]: Method call with subscriberUID:', subscriberUID)
    this.socket.unsubscribeFromStream(subscriberUID)
  }

  /**
   * jsAPI
   * The library calls getMarks to request marks for the visible bar range.
   * The library assumes that you call GetMarksCallback once per getMarks call.
   * Pass an array of Mark objects as a callback parameter.
   * Only ten marks can be attached to a bar.
   * The time of each mark must match the time of a bar.
   * For example, if the bar times are 2023-01-01, 2023-01-08, and 2023-01-15, then a mark cannot have the time 2023-01-05.
   * 该接口只能显示圆形的标记，标记里可以显示一个或者两个字母，只能定位标记的X轴坐标，无法定位Y轴坐标，Y坐标会自动决定
   * 并不适合用于标记挂单买卖点，而适合用于标记一些别的东西
   * @param symbolInfo
   * @param startDate
   * @param endDate
   * @param onDataCallback
   * @param resolution
   */
  public async getMarks(symbolInfo, startDate, endDate, onDataCallback, resolution) {
    console.log('getMarks')
    // 调用onDataCallback回调就可以在图上显示标记，可以在此处进行定时轮询或者订阅WSS，然后择机触发onDataCallback
    onDataCallback([
      {
        id: 1,
        time: 1723850100,
        color: 'red',
        text: ['This is the mark pop-up text.'],
        label: '买',
        labelFontColor: 'blue',
        minSize: 25
      }
    ])
  }
  /** jsAPI
   * The library calls getTimescaleMarks to request timescale marks for the visible bar range.
   * The library assumes that you call GetMarksCallback once per getTimescaleMarks call.
   * Pass an array of TimescaleMark objects as a callback parameter.
   * <caution> These method is called only if your datafeed supports marks.
   * 该接口能指定标记的形状，标记里可以显示一个或者两个字母，标记会显示在X轴附近，适合用于标记一段时间区间，并不适合用于标记挂单买卖点，
   * @param symbolInfo
   * @param startDate
   * @param endDate
   * @param onDataCallback
   * @param resolution
   */
  public async getTimescaleMarks(symbolInfo, startDate, endDate, onDataCallback, resolution) {
    // optional
    console.log('getTimescaleMarks')

    let marks = <any>[]

    marks = [
      {
        id: 1,
        time: 1723850100,
        color: 'red',
        label: 'T',
        minSize: 30,
        tooltip: ['Amet', 'Consectetur', 'Adipiscing', 'Elit']
      },
      {
        id: 2,
        time: 1723851300,
        color: 'green',
        label: 'x',
        minSize: 30,
        tooltip: ['Amet', 'Consectetur', 'Adipiscing', 'Elit']
      },
    ]

    onDataCallback(marks)
  }
  /**
   * jsAPI
   * 不定义的时候自动获取机器的时间
   * @param ServerTimeCallback
   */
  // public async getServerTime(ServerTimeCallback) {
  //   console.log('getServerTime')
  //   // ServerTimeCallback(114514)
  // }
}
