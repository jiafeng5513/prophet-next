# -*- coding: utf-8 -*-
"""
===================================
OKXFetcher - 欧易数据源 (Priority 7)
===================================

数据来源：OKX REST API v5
特点：加密货币历史K线数据，公开接口无需API Key

API文档：
- 近期K线: GET /api/v5/market/candles (最近1440条)
- 历史K线: GET /api/v5/market/history-candles (更早期数据)
- Base URL: https://www.okx.com
- 每次最多返回300条

限制：
- 速率限制：20次/2s per instrument
- 交易对格式: BTC-USDT (以'-'分隔)
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

# OKX K线间隔映射: 内部格式 -> OKX格式
INTERVAL_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "1w": "1W",
    "1M": "1M",
    "3M": "3M",
}

# 反向映射: OKX格式 -> 内部格式
INTERVAL_MAP_REVERSE = {v: k for k, v in INTERVAL_MAP.items()}

MAX_KLINES_PER_REQUEST = 300
BASE_URL = "https://www.okx.com"


def to_okx_inst_id(symbol: str) -> str:
    """
    将内部统一格式转为OKX instId格式。
    BTC-USDT -> BTC-USDT (OKX本身使用'-'分隔)
    BTCUSDT -> BTC-USDT
    """
    upper = symbol.strip().upper()
    if "-" in upper:
        return upper

    # 尝试拆分纯字母格式
    for quote in ("USDT", "USDC", "BTC", "ETH"):
        if upper.endswith(quote) and len(upper) > len(quote):
            base = upper[: -len(quote)]
            return f"{base}-{quote}"
    return upper


def from_okx_inst_id(inst_id: str) -> str:
    """
    将OKX instId转为内部统一格式。
    BTC-USDT -> BTC-USDT (已经是统一格式)
    """
    return inst_id.upper()


class OKXFetcher(BaseFetcher):
    """
    OKX REST API v5 数据源

    用于获取加密货币历史K线数据。
    公开市场数据无需API Key，但有速率限制。
    """

    name = "OKXFetcher"
    priority = 7

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None,
                 passphrase: Optional[str] = None, base_url: Optional[str] = None,
                 proxy: Optional[str] = None):
        self._api_key = api_key
        self._secret_key = secret_key
        self._passphrase = passphrase
        self._base_url = (base_url or BASE_URL).rstrip("/")
        self._proxy = proxy
        self._session = self._create_session()
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests (20/2s = 10/s)

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
            "Content-Type": "application/json",
        })
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

    def _request_candles(self, inst_id: str, bar: str = "1D",
                         after: Optional[str] = None,
                         before: Optional[str] = None,
                         limit: int = MAX_KLINES_PER_REQUEST,
                         use_history: bool = False) -> List[List[str]]:
        """
        请求OKX K线数据。

        Args:
            inst_id: 交易对ID，如 'BTC-USDT'
            bar: K线周期
            after: 请求此时间戳之前的数据 (分页用，ISO时间戳ms)
            before: 请求此时间戳之后的数据
            limit: 限制条数 (max 300)
            use_history: 是否使用历史K线接口

        Returns:
            List of candle arrays: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        """
        self._rate_limit()

        endpoint = "/api/v5/market/history-candles" if use_history else "/api/v5/market/candles"
        params = {
            "instId": inst_id,
            "bar": bar,
            "limit": str(min(limit, MAX_KLINES_PER_REQUEST)),
        }
        if after is not None:
            params["after"] = str(after)
        if before is not None:
            params["before"] = str(before)

        url = f"{self._base_url}{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=15)
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"[OKXFetcher] 请求失败: {e}") from e

        if resp.status_code == 429:
            raise RateLimitError("[OKXFetcher] 速率限制，请稍后重试")
        if resp.status_code != 200:
            raise DataFetchError(
                f"[OKXFetcher] HTTP {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        if data.get("code") != "0":
            msg = data.get("msg", "Unknown error")
            raise DataFetchError(f"[OKXFetcher] API错误: {msg}")

        return data.get("data", [])

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取OKX K线原始数据，自动分页处理。

        OKX的翻页逻辑：使用 after 参数（请求该时间戳之前的数据），
        数据返回从新到旧排列。
        """
        inst_id = to_okx_inst_id(stock_code)
        bar = "1D"  # 默认日线

        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(
            (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp() * 1000
        ) - 1

        all_candles = []

        # 先尝试 /candles 接口（最近1440条）
        after_cursor = str(end_ts + 1)  # after表示"请求此时间之前的数据"
        use_history = False
        max_pages = 50  # 安全阀

        for _ in range(max_pages):
            candles = self._request_candles(
                inst_id=inst_id,
                bar=bar,
                after=after_cursor,
                limit=MAX_KLINES_PER_REQUEST,
                use_history=use_history,
            )

            if not candles:
                if not use_history:
                    # 切换到history-candles接口获取更早期数据
                    use_history = True
                    continue
                break

            # OKX返回数据从新到旧排列，candles[0]是最新的
            for candle in candles:
                ts = int(candle[0])
                if ts < start_ts:
                    # 已经超出请求范围
                    all_candles.append(candle)
                    # 设置标记，后面过滤
                    break
                all_candles.append(candle)

            # 检查是否已经获取到起始时间之前的数据
            oldest_ts = int(candles[-1][0])
            if oldest_ts <= start_ts:
                break

            # 下一页: after = 最旧一条的时间戳
            after_cursor = str(oldest_ts)

            if len(candles) < MAX_KLINES_PER_REQUEST:
                if not use_history:
                    use_history = True
                    continue
                break

        if not all_candles:
            return pd.DataFrame()

        # 转为DataFrame
        df = pd.DataFrame(all_candles, columns=[
            "ts", "open", "high", "low", "close", "vol",
            "vol_ccy", "vol_ccy_quote", "confirm"
        ])

        # 过滤在时间范围内的数据
        df["ts"] = pd.to_numeric(df["ts"], errors="coerce")
        df = df[(df["ts"] >= start_ts) & (df["ts"] <= end_ts)]

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将OKX原始数据标准化"""
        if df.empty:
            return df

        result = pd.DataFrame()
        result["date"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
        result["open"] = pd.to_numeric(df["open"], errors="coerce")
        result["high"] = pd.to_numeric(df["high"], errors="coerce")
        result["low"] = pd.to_numeric(df["low"], errors="coerce")
        result["close"] = pd.to_numeric(df["close"], errors="coerce")
        result["volume"] = pd.to_numeric(df["vol"], errors="coerce")
        result["amount"] = pd.to_numeric(df["vol_ccy_quote"], errors="coerce")

        # 按时间升序排序
        result = result.sort_values("date", ascending=True).reset_index(drop=True)

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
        inst_id = to_okx_inst_id(symbol)
        bar = INTERVAL_MAP.get(interval, "1D")

        start_ts = None
        end_ts = None
        if start_date:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        if end_date:
            end_ts = int(
                (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp() * 1000
            ) - 1

        all_candles = []
        after_cursor = str(end_ts + 1) if end_ts else None
        use_history = False
        remaining = limit

        for _ in range(50):
            batch_limit = min(remaining, MAX_KLINES_PER_REQUEST)
            candles = self._request_candles(
                inst_id=inst_id,
                bar=bar,
                after=after_cursor,
                limit=batch_limit,
                use_history=use_history,
            )

            if not candles:
                if not use_history:
                    use_history = True
                    continue
                break

            for candle in candles:
                ts = int(candle[0])
                if start_ts and ts < start_ts:
                    break
                all_candles.append(candle)
                remaining -= 1
                if remaining <= 0:
                    break

            if remaining <= 0:
                break

            oldest_ts = int(candles[-1][0])
            if start_ts and oldest_ts <= start_ts:
                break

            after_cursor = str(oldest_ts)

            if len(candles) < batch_limit:
                if not use_history:
                    use_history = True
                    continue
                break

        if not all_candles:
            return pd.DataFrame()

        df = pd.DataFrame(all_candles, columns=[
            "ts", "open", "high", "low", "close", "vol",
            "vol_ccy", "vol_ccy_quote", "confirm"
        ])

        result = pd.DataFrame()
        result["date"] = pd.to_datetime(pd.to_numeric(df["ts"], errors="coerce").astype(int), unit="ms")
        result["open"] = pd.to_numeric(df["open"], errors="coerce")
        result["high"] = pd.to_numeric(df["high"], errors="coerce")
        result["low"] = pd.to_numeric(df["low"], errors="coerce")
        result["close"] = pd.to_numeric(df["close"], errors="coerce")
        result["volume"] = pd.to_numeric(df["vol"], errors="coerce")
        result["amount"] = pd.to_numeric(df["vol_ccy_quote"], errors="coerce")

        result = result.sort_values("date", ascending=True).reset_index(drop=True)
        result["pct_chg"] = result["close"].pct_change() * 100
        result["pct_chg"] = result["pct_chg"].fillna(0.0)

        return result
