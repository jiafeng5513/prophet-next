// Makes requests to Binance API
export async function makeApiRequest(path: string) {
  console.log(`[makeApiRequest] ${path}`)
  try {
    const response = await fetch(`https://api.binance.com/${path}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return response.json()
  } catch (error) {
    throw new Error(`[Binance] request error: ${error}`)
  }
}

export async function makeBinanceRequest(path: string) {
  try {
    const url = `https://api.binance.com/${path}`

    console.log(`[makeBinanceRequest] Fetching: ${url}`)

    // GET 请求不需要设置 Content-Type 头，避免触发 CORS 预检请求
    // Binance API 支持简单的 GET 请求，不需要额外的请求头
    const response = await fetch(url, {
      method: 'GET',
      // 不设置 headers，让浏览器使用默认值
      mode: 'cors' // 明确指定 CORS 模式
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[makeBinanceRequest] HTTP error! status: ${response.status}, body: ${errorText}`)
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    console.log(`[makeBinanceRequest] Success: ${path}`)
    return data
  } catch (error) {
    console.error(`[makeBinanceRequest] Error for ${path}:`, error)
    throw new Error(`[Binance] request error: ${error}`)
  }
}

// Generates a symbol ID from a pair of the coins
export function generateSymbol(exchange: string, fromSymbol: string, toSymbol: string) {
  const short = `${fromSymbol}/${toSymbol}`
  return {
    short,
    full: `${exchange}:${short}`
  }
}

export function parseFullSymbol(fullSymbol: string) {
  console.log(`[parseFullSymbol] fullSymbol = ${fullSymbol}`)
  // 支持格式: "Binance:BTC/USDT" 或 "BTC/USDT"
  const match = fullSymbol.match(/^(?:(\w+):)?(\w+)\/(\w+)$/)
  if (!match) {
    console.error(`[parseFullSymbol] Failed to parse: ${fullSymbol}`)
    return null
  }
  const exchange = match[1] || 'Binance'
  const symbol = `${match[2]}${match[3]}` // BTCUSDT
  console.log(`[parseFullSymbol] Parsed: exchange=${exchange}, symbol=${symbol}`)
  return { exchange, symbol }
}

export function priceScale(tickSize: string | number) {
  if (Number(tickSize) >= 1) {
    return Math.pow(10, Number(tickSize))
  } else {
    return Math.round(1 / parseFloat(String(tickSize)))
  }
}
