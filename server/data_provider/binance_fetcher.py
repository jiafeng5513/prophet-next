# -*- coding: utf-8 -*-
"""
===================================
BinanceFetcher - 币安数据源 (Priority 6)
===================================

数据来源：Binance REST API
特点：加密货币历史K线数据，公开接口无需API Key

API文档：
- 历史K线: GET /api/v3/klines
- Base URL: https://api.binance.com (或 https://data-api.binance.vision)
- 单次最多返回1000条，需分页获取

限制：
- IP限流：1200 req/min (无API Key)
- 单次最大1000条K线
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import BaseFetcher, DataFetchError, RateLimitError

logger = logging.getLogger(__name__)

# Binance K线间隔映射: 内部格式 -> Binance格式
INTERVAL_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}

# 每种间隔对应的毫秒数（用于分页计算）
INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
    "3d": 259_200_000,
    "1w": 604_800_000,
    "1M": 2_592_000_000,
}

MAX_KLINES_PER_REQUEST = 1000
BASE_URL = "https://api.binance.com"
DATA_URL = "https://data-api.binance.vision"


def to_binance_symbol(symbol: str) -> str:
    """
    将内部统一格式转为Binance格式。
    内部格式: BTC-USDT -> BTCUSDT
    """
    return symbol.replace("-", "").upper()


def from_binance_symbol(symbol: str) -> str:
    """
    将Binance格式转为内部统一格式。
    BTCUSDT -> BTC-USDT (简单策略: 以常见quote结尾做切割)
    """
    upper = symbol.upper()
    for quote in ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"):
        if upper.endswith(quote) and len(upper) > len(quote):
            base = upper[: -len(quote)]
            return f"{base}-{quote}"
    return upper


def is_crypto_code(code: str) -> bool:
    """判断是否为加密货币代码。"""
    normalized = (code or "").strip().upper()
    # 包含 '-' 分隔的交易对格式
    if "-" in normalized:
        parts = normalized.split("-")
        if len(parts) == 2 and parts[0].isalpha() and parts[1].isalpha():
            return True
    # 已知 quote 后缀的纯字母形式
    for quote in ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"):
        if normalized.endswith(quote) and len(normalized) > len(quote) and normalized[: -len(quote)].isalpha():
            return True
    return False


class BinanceFetcher(BaseFetcher):
    """
    Binance REST API 数据源

    用于获取加密货币历史K线数据。
    公开市场数据无需API Key，但有IP速率限制。
    """

    name = "BinanceFetcher"
    priority = 6

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 base_url: Optional[str] = None, proxy: Optional[str] = None):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = (base_url or DATA_URL).rstrip("/")
        self._proxy = proxy
        self._session = self._create_session()
        self._last_request_time = 0.0
        self._min_request_interval = 0.05  # 50ms between requests (1200/min = 20/s)

    def _create_session(self) -> requests.Session:
        """创建带重试机制的HTTP Session"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HiveLogic/1.0",
        })
        if self._api_key:
            session.headers["X-MBX-APIKEY"] = self._api_key
        if self._proxy:
            session.proxies = {"https": self._proxy, "http": self._proxy}
        return session

    def _rate_limit(self):
        """简单的速率限制"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request_klines(self, symbol: str, interval: str,
                        start_time: Optional[int] = None,
                        end_time: Optional[int] = None,
                        limit: int = MAX_KLINES_PER_REQUEST) -> List[List]:
        """
        请求Binance K线数据。

        Returns:
            List of kline arrays:
            [open_time, open, high, low, close, volume, close_time,
             quote_volume, trades, taker_buy_base, taker_buy_quote, ignore]
        """
        self._rate_limit()

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, MAX_KLINES_PER_REQUEST),
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        url = f"{self._base_url}/api/v3/klines"
        try:
            resp = self._session.get(url, params=params, timeout=15)
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"[BinanceFetcher] 请求失败: {e}") from e

        if resp.status_code == 429 or resp.status_code == 418:
            retry_after = resp.headers.get("Retry-After", "60")
            raise RateLimitError(
                f"[BinanceFetcher] 速率限制，需等待 {retry_after}s"
            )
        if resp.status_code != 200:
            raise DataFetchError(
                f"[BinanceFetcher] HTTP {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json()

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取Binance K线原始数据，自动分页处理。

        Args:
            stock_code: 交易对代码，如 'BTC-USDT' 或 'BTCUSDT'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
        """
        binance_symbol = to_binance_symbol(stock_code)
        interval = "1d"  # 默认日线

        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(
            (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp() * 1000
        ) - 1  # 当天23:59:59.999

        all_klines = []
        current_start = start_ts

        while current_start <= end_ts:
            klines = self._request_klines(
                symbol=binance_symbol,
                interval=interval,
                start_time=current_start,
                end_time=end_ts,
                limit=MAX_KLINES_PER_REQUEST,
            )

            if not klines:
                break

            all_klines.extend(klines)

            # 下一页从最后一条K线的close_time + 1开始
            last_close_time = klines[-1][6]
            current_start = last_close_time + 1

            # 如果返回条数小于limit，说明已获取完毕
            if len(klines) < MAX_KLINES_PER_REQUEST:
                break

        if not all_klines:
            return pd.DataFrame()

        # 转为DataFrame
        df = pd.DataFrame(all_klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将Binance原始数据标准化"""
        if df.empty:
            return df

        result = pd.DataFrame()
        result["date"] = pd.to_datetime(df["open_time"], unit="ms")
        result["open"] = pd.to_numeric(df["open"], errors="coerce")
        result["high"] = pd.to_numeric(df["high"], errors="coerce")
        result["low"] = pd.to_numeric(df["low"], errors="coerce")
        result["close"] = pd.to_numeric(df["close"], errors="coerce")
        result["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        result["amount"] = pd.to_numeric(df["quote_volume"], errors="coerce")

        # 计算涨跌幅
        result["pct_chg"] = result["close"].pct_change() * 100
        result["pct_chg"] = result["pct_chg"].fillna(0.0)

        return result

    def fetch_klines(self, symbol: str, interval: str = "1d",
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: int = 500) -> pd.DataFrame:
        """
        获取指定间隔的K线数据（扩展接口）。

        Args:
            symbol: 交易对，如 'BTC-USDT'
            interval: K线间隔，如 '1h', '4h', '1d'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            limit: 最大获取条数
        """
        binance_symbol = to_binance_symbol(symbol)
        binance_interval = INTERVAL_MAP.get(interval, interval)

        start_ts = None
        end_ts = None
        if start_date:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        if end_date:
            end_ts = int(
                (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp() * 1000
            ) - 1

        all_klines = []
        current_start = start_ts
        remaining = limit

        while remaining > 0:
            batch_limit = min(remaining, MAX_KLINES_PER_REQUEST)
            klines = self._request_klines(
                symbol=binance_symbol,
                interval=binance_interval,
                start_time=current_start,
                end_time=end_ts,
                limit=batch_limit,
            )

            if not klines:
                break

            all_klines.extend(klines)
            remaining -= len(klines)

            last_close_time = klines[-1][6]
            current_start = last_close_time + 1

            if len(klines) < batch_limit:
                break

        if not all_klines:
            return pd.DataFrame()

        df = pd.DataFrame(all_klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        result = pd.DataFrame()
        result["date"] = pd.to_datetime(df["open_time"], unit="ms")
        result["open"] = pd.to_numeric(df["open"], errors="coerce")
        result["high"] = pd.to_numeric(df["high"], errors="coerce")
        result["low"] = pd.to_numeric(df["low"], errors="coerce")
        result["close"] = pd.to_numeric(df["close"], errors="coerce")
        result["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        result["amount"] = pd.to_numeric(df["quote_volume"], errors="coerce")
        result["pct_chg"] = result["close"].pct_change() * 100
        result["pct_chg"] = result["pct_chg"].fillna(0.0)

        return result
