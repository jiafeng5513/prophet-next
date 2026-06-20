/**
 * Trading Hours — 交易时段配置与判定
 *
 * 支持 A 股、港股、美股、加密货币、期货市场的交易时段定义。
 * 用于图表非交易时段折叠等场景。
 */

export type MarketType = 'A_SHARE' | 'HK' | 'US' | 'CRYPTO' | 'FUTURES'

export interface TradingSession {
  /** 开始时间 "HH:mm" */
  start: string
  /** 结束时间 "HH:mm" */
  end: string
}

export interface MarketConfig {
  sessions: TradingSession[]
  timezone: string
  /** 是否 24 小时交易 */
  is24h: boolean
}

/** 各市场交易时段配置 */
export const MARKET_CONFIGS: Record<MarketType, MarketConfig> = {
  A_SHARE: {
    sessions: [
      { start: '09:30', end: '11:30' },
      { start: '13:00', end: '15:00' }
    ],
    timezone: 'Asia/Shanghai',
    is24h: false
  },
  HK: {
    sessions: [
      { start: '09:30', end: '12:00' },
      { start: '13:00', end: '16:00' }
    ],
    timezone: 'Asia/Hong_Kong',
    is24h: false
  },
  US: {
    sessions: [
      { start: '09:30', end: '16:00' }
    ],
    timezone: 'America/New_York',
    is24h: false
  },
  CRYPTO: {
    sessions: [
      { start: '00:00', end: '23:59' }
    ],
    timezone: 'UTC',
    is24h: true
  },
  FUTURES: {
    sessions: [
      { start: '09:00', end: '11:30' },
      { start: '13:30', end: '15:00' },
      { start: '21:00', end: '23:00' }
    ],
    timezone: 'Asia/Shanghai',
    is24h: false
  }
}

/**
 * 从标的代码推断市场类型
 */
export function detectMarketType(symbol: string): MarketType {
  const s = symbol.toUpperCase()

  // 加密货币: BTCUSDT, ETH/USDT, Binance:, OKX:
  if (/^(BINANCE|OKX):/i.test(symbol) || /USDT|BUSD|BTC$/.test(s)) {
    return 'CRYPTO'
  }

  // A 股: 6xxxxx (SSE), 0xxxxx/3xxxxx (SZSE), SSE:, SZSE:
  if (/^(SSE|SZSE|BSE):/i.test(symbol) || /^[036]\d{5}$/.test(s)) {
    return 'A_SHARE'
  }

  // 港股: 5 位数字 或 HK:
  if (/^HK:/i.test(symbol) || /^\d{5}$/.test(s)) {
    return 'HK'
  }

  // 默认美股
  return 'US'
}

/**
 * 获取指定市场的交易时段配置
 */
export function getMarketConfig(market: MarketType): MarketConfig {
  return MARKET_CONFIGS[market]
}

/**
 * 解析 "HH:mm" 为当天的分钟数
 */
function parseTimeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

/**
 * 判断某个时间是否在交易时段内
 * @param minutes 当天分钟数 (0-1439)
 * @param market 市场类型
 */
export function isInTradingHours(minutes: number, market: MarketType): boolean {
  const config = MARKET_CONFIGS[market]
  if (config.is24h) return true

  return config.sessions.some(session => {
    const start = parseTimeToMinutes(session.start)
    const end = parseTimeToMinutes(session.end)
    // 处理跨午夜的情况 (期货夜盘)
    if (start > end) {
      return minutes >= start || minutes <= end
    }
    return minutes >= start && minutes <= end
  })
}

/**
 * 生成 TradingView 格式的 session 字符串
 * 例: "0930-1130,1300-1500"
 */
export function toTradingViewSession(market: MarketType): string {
  const config = MARKET_CONFIGS[market]
  if (config.is24h) return '24x7'

  return config.sessions
    .map(s => `${s.start.replace(':', '')}-${s.end.replace(':', '')}`)
    .join(',')
}

/**
 * 获取 TradingView timezone 字符串
 */
export function getTradingViewTimezone(market: MarketType): string {
  return MARKET_CONFIGS[market].timezone
}
