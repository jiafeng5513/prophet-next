# -*- coding: utf-8 -*-
"""
===================================
品种列表发现服务
===================================

职责：
1. 统一各市场品种列表获取接口
2. 内存缓存（TTL 1小时）避免频繁调外部API
3. 为批量下载提供品种列表支持

支持市场：
- crypto_binance: 通过 Binance exchangeInfo API 获取 USDT 现货交易对
- crypto_okx: 通过 OKX instruments API 获取现货交易对
- cn: 通过 Tushare/Baostock 获取A股列表
- us: 通过 TickFlow 或 YFinance 获取美股列表
- hk: 通过 TickFlow 或 LongBridge 获取港股列表
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# 缓存有效期: 1小时
CACHE_TTL_SECONDS = 3600


class SymbolListService:
    """统一品种列表发现服务"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_symbols(self, market: str) -> List[Dict[str, str]]:
        """
        获取指定市场的全部可下载品种列表。

        Args:
            market: 市场标识 - "crypto_binance", "crypto_okx", "cn", "us", "hk"

        Returns:
            品种列表 [{"symbol": "BTCUSDT", "name": "BTC/USDT"}, ...]
        """
        # 检查缓存
        cached = self._get_cached(market)
        if cached is not None:
            return cached

        # 根据市场调用对应方法
        dispatch = {
            "crypto_binance": self._fetch_binance_symbols,
            "crypto_okx": self._fetch_okx_symbols,
            "cn": self._fetch_cn_symbols,
            "us": self._fetch_us_symbols,
            "hk": self._fetch_hk_symbols,
        }

        fetcher = dispatch.get(market)
        if not fetcher:
            logger.warning(f"[SymbolListService] 未知市场: {market}")
            return []

        try:
            symbols = fetcher()
            self._set_cached(market, symbols)
            logger.info(f"[SymbolListService] {market} 获取 {len(symbols)} 个品种")
            return symbols
        except Exception as e:
            logger.error(f"[SymbolListService] {market} 获取品种列表失败: {e}")
            return []

    def get_symbol_count(self, market: str) -> int:
        """获取品种数量（优先用缓存）"""
        symbols = self.get_symbols(market)
        return len(symbols)

    def invalidate_cache(self, market: Optional[str] = None):
        """清除缓存"""
        with self._lock:
            if market:
                self._cache.pop(market, None)
            else:
                self._cache.clear()

    # ==================== 缓存管理 ====================

    def _get_cached(self, market: str) -> Optional[List[Dict[str, str]]]:
        with self._lock:
            entry = self._cache.get(market)
            if entry and time.time() - entry["time"] < CACHE_TTL_SECONDS:
                return entry["data"]
        return None

    def _set_cached(self, market: str, data: List[Dict[str, str]]):
        with self._lock:
            self._cache[market] = {"data": data, "time": time.time()}

    # ==================== Binance ====================

    def _fetch_binance_symbols(self) -> List[Dict[str, str]]:
        """
        获取 Binance 现货 USDT 交易对。
        API: GET https://api.binance.com/api/v3/exchangeInfo
        """
        url = "https://api.binance.com/api/v3/exchangeInfo"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[SymbolListService] Binance exchangeInfo 请求失败: {e}")
            raise

        symbols = []
        for item in data.get("symbols", []):
            # 只取 TRADING 状态的 USDT 现货交易对
            if (item.get("status") == "TRADING"
                    and item.get("quoteAsset") == "USDT"
                    and item.get("isSpotTradingAllowed", False)):
                symbol = item["symbol"]  # e.g. "BTCUSDT"
                base = item.get("baseAsset", "")
                symbols.append({
                    "symbol": symbol,
                    "name": f"{base}/USDT",
                })

        # 按交易量排序（如果有权重信息的话，暂按字母排序）
        symbols.sort(key=lambda x: x["symbol"])
        return symbols

    # ==================== OKX ====================

    def _fetch_okx_symbols(self) -> List[Dict[str, str]]:
        """
        获取 OKX 现货交易对。
        API: GET https://www.okx.com/api/v5/public/instruments?instType=SPOT
        """
        url = "https://www.okx.com/api/v5/public/instruments"
        params = {"instType": "SPOT"}
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[SymbolListService] OKX instruments 请求失败: {e}")
            raise

        symbols = []
        for item in data.get("data", []):
            inst_id = item.get("instId", "")  # e.g. "BTC-USDT"
            state = item.get("state", "")
            quote_ccy = item.get("quoteCcy", "")

            # 只取活跃的 USDT 交易对
            if state == "live" and quote_ccy == "USDT":
                base_ccy = item.get("baseCcy", "")
                symbols.append({
                    "symbol": inst_id,
                    "name": f"{base_ccy}/USDT",
                })

        symbols.sort(key=lambda x: x["symbol"])
        return symbols

    # ==================== A股 ====================

    def _fetch_cn_symbols(self) -> List[Dict[str, str]]:
        """
        获取A股全部上市股票列表。
        优先使用 Tushare，回退到 Baostock。
        """
        # 尝试 Tushare
        symbols = self._try_tushare_stock_list()
        if symbols:
            return symbols

        # 回退到 Baostock
        symbols = self._try_baostock_stock_list()
        if symbols:
            return symbols

        logger.warning("[SymbolListService] A股品种列表获取失败：无可用数据源")
        return []

    def _try_tushare_stock_list(self) -> List[Dict[str, str]]:
        """尝试通过 TushareFetcher 获取A股列表"""
        try:
            from data_provider.base import DataFetcherManager
            mgr = DataFetcherManager()
            fetchers = mgr._get_fetchers_snapshot()

            for f in fetchers:
                if f.name == "TushareFetcher" and hasattr(f, "get_stock_list"):
                    df = f.get_stock_list()
                    if df is not None and not df.empty:
                        symbols = []
                        for _, row in df.iterrows():
                            symbols.append({
                                "symbol": str(row["code"]),
                                "name": str(row.get("name", "")),
                            })
                        return symbols
        except Exception as e:
            logger.debug(f"[SymbolListService] Tushare stock_list failed: {e}")
        return []

    def _try_baostock_stock_list(self) -> List[Dict[str, str]]:
        """尝试通过 BaostockFetcher 获取A股列表"""
        try:
            from data_provider.base import DataFetcherManager
            mgr = DataFetcherManager()
            fetchers = mgr._get_fetchers_snapshot()

            for f in fetchers:
                if f.name == "BaostockFetcher" and hasattr(f, "get_stock_list"):
                    df = f.get_stock_list()
                    if df is not None and not df.empty:
                        symbols = []
                        for _, row in df.iterrows():
                            symbols.append({
                                "symbol": str(row["code"]),
                                "name": str(row.get("name", "")),
                            })
                        return symbols
        except Exception as e:
            logger.debug(f"[SymbolListService] Baostock stock_list failed: {e}")
        return []

    # ==================== 美股 ====================

    def _fetch_us_symbols(self) -> List[Dict[str, str]]:
        """
        获取美股品种列表。
        优先使用 TickFlow，回退到硬编码主要指数/ETF。
        """
        symbols = self._try_tickflow_symbols("us_stock")
        if symbols:
            return symbols

        # 回退: 常见美股指数 + 主要ETF + 大盘股
        logger.info("[SymbolListService] 美股使用默认品种列表")
        return self._get_default_us_symbols()

    def _get_default_us_symbols(self) -> List[Dict[str, str]]:
        """美股默认品种列表（主要指数+ETF+大盘股）"""
        defaults = [
            ("SPY", "SPDR S&P 500 ETF"),
            ("QQQ", "Invesco QQQ Trust"),
            ("DIA", "SPDR Dow Jones ETF"),
            ("IWM", "iShares Russell 2000"),
            ("AAPL", "Apple Inc"),
            ("MSFT", "Microsoft Corp"),
            ("GOOGL", "Alphabet Inc"),
            ("AMZN", "Amazon.com Inc"),
            ("NVDA", "NVIDIA Corp"),
            ("META", "Meta Platforms"),
            ("TSLA", "Tesla Inc"),
            ("BRK.B", "Berkshire Hathaway B"),
            ("JPM", "JPMorgan Chase"),
            ("V", "Visa Inc"),
            ("UNH", "UnitedHealth Group"),
            ("MA", "Mastercard Inc"),
            ("HD", "Home Depot"),
            ("PG", "Procter & Gamble"),
            ("JNJ", "Johnson & Johnson"),
            ("XOM", "Exxon Mobil"),
        ]
        return [{"symbol": s, "name": n} for s, n in defaults]

    # ==================== 港股 ====================

    def _fetch_hk_symbols(self) -> List[Dict[str, str]]:
        """
        获取港股品种列表。
        优先使用 TickFlow，回退到默认列表。
        """
        symbols = self._try_tickflow_symbols("hk_stock")
        if symbols:
            return symbols

        logger.info("[SymbolListService] 港股使用默认品种列表")
        return self._get_default_hk_symbols()

    def _get_default_hk_symbols(self) -> List[Dict[str, str]]:
        """港股默认品种列表（恒生指数成分股 + 主要ETF）"""
        defaults = [
            ("00700", "腾讯控股"),
            ("09988", "阿里巴巴"),
            ("03690", "美团"),
            ("09999", "网易"),
            ("09618", "京东集团"),
            ("01810", "小米集团"),
            ("00941", "中国移动"),
            ("00388", "香港交易所"),
            ("02318", "中国平安"),
            ("00005", "汇丰控股"),
            ("01299", "友邦保险"),
            ("02020", "安踏体育"),
            ("09888", "百度集团"),
            ("01024", "快手"),
            ("00981", "中芯国际"),
            ("02800", "盈富基金"),
            ("03033", "南方恒生科技ETF"),
            ("02269", "药明生物"),
            ("00883", "中国海洋石油"),
            ("01211", "比亚迪"),
        ]
        return [{"symbol": s, "name": n} for s, n in defaults]

    # ==================== TickFlow 通用 ====================

    def _try_tickflow_symbols(self, market_type: str) -> List[Dict[str, str]]:
        """尝试通过 TickFlowFetcher 获取品种列表"""
        try:
            from data_provider.base import DataFetcherManager
            mgr = DataFetcherManager()
            fetchers = mgr._get_fetchers_snapshot()

            for f in fetchers:
                if f.name == "TickFlowFetcher" and hasattr(f, "get_symbol_list"):
                    items = f.get_symbol_list(market_type)
                    if items:
                        symbols = []
                        for item in items:
                            symbols.append({
                                "symbol": str(item.get("symbol", item.get("code", ""))),
                                "name": str(item.get("name", "")),
                            })
                        return symbols
        except Exception as e:
            logger.debug(f"[SymbolListService] TickFlow {market_type} failed: {e}")
        return []


# ==================== 全局单例 ====================

_service_instance: Optional[SymbolListService] = None
_service_lock = threading.Lock()


def get_symbol_list_service() -> SymbolListService:
    """获取全局 SymbolListService 单例"""
    global _service_instance
    if _service_instance is None:
        with _service_lock:
            if _service_instance is None:
                _service_instance = SymbolListService()
    return _service_instance
