// import fetch from 'node-fetch';
import axios, { AxiosProxyConfig } from 'axios'

const proxyProtocol = 'http'
const proxyHost = '127.0.0.1'
const proxyPort = 7890

class ProxyConfig implements AxiosProxyConfig {
  host: string
  port: number
  protocol?: string | undefined
  constructor(protocol: string | undefined, host: string, port: number) {
    this.host = host
    this.port = port
    this.protocol = protocol
  }
}

const proxyAgent = new ProxyConfig(proxyProtocol, proxyHost, proxyPort)

// Makes requests to Binance API
export async function makeApiRequest(path: string) {
  console.log(`[makeApiRequest] ${path}`)
  try {
    const response = await fetch(`https://api.binance.com/${path}`)
    return response.json()
  } catch (error) {
    throw new Error(`[Binance] request error: ${error}`)
  }
}

export async function makeBinanceRequest(path: string) {
  try {
    const url = `https://api.binance.com/${path}`

    console.log(`try to get ${url}`)

    const response = await axios.get(`${url}`, {
      proxy: proxyAgent,
      timeout: 30 * 1000
    })

    return response.data
  } catch (error) {
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
  const match = fullSymbol.match(/^(\w+):(\w+)\/(\w+)$/)
  if (!match) {
    return null
  }
  return { exchange: match[1], symbol: `${match[2]}${match[3]}` }
}

export function priceScale(tickSize: string | number) {
  if (Number(tickSize) >= 1) {
    return Math.pow(10, Number(tickSize))
  } else {
    return Math.round(1 / parseFloat(String(tickSize)))
  }
}
