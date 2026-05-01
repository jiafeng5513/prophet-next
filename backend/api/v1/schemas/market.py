# -*- coding: utf-8 -*-
"""
===================================
市场数据相关模型 (标的浏览器)
===================================

职责：
1. 定义标的信息模型 (SymbolInfo)
2. 定义市场类型模型 (MarketType)
3. 定义统一 K 线数据模型 (兼容 TradingView UDF)
4. 定义 API 请求/响应模型
"""

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


# === 枚举定义 ===

class MarketTypeEnum(str, Enum):
    """支持的市场类型"""
    CRYPTO = "crypto"
    CN_STOCK = "cn_stock"
    CN_ETF = "cn_etf"
    CN_FUTURES = "cn_futures"
    HK_STOCK = "hk_stock"
    US_STOCK = "us_stock"


class ExchangeEnum(str, Enum):
    """支持的交易所"""
    BINANCE = "Binance"
    OKX = "OKX"
    SSE = "SSE"          # 上海证券交易所
    SZSE = "SZSE"        # 深圳证券交易所
    BSE = "BSE"          # 北京证券交易所
    CFFEX = "CFFEX"      # 中国金融期货交易所
    HKEX = "HKEX"        # 香港交易所
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"


class DataSourceEnum(str, Enum):
    """数据源标识"""
    BINANCE = "binance"
    OKX = "okx"
    AKSHARE = "akshare"
    TICKFLOW = "tickflow"


# === 数据模型 ===

class MarketType(BaseModel):
    """市场类型定义"""

    type: MarketTypeEnum = Field(..., description="市场类型标识")
    name: str = Field(..., description="市场类型名称 (中文)")
    description: str = Field("", description="市场描述")
    data_source: DataSourceEnum = Field(..., description="默认数据源")
    icon: str = Field("", description="图标标识")
    enabled: bool = Field(True, description="是否启用")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "cn_stock",
                "name": "A股",
                "description": "中国A股市场",
                "data_source": "akshare",
                "icon": "stock",
                "enabled": True,
            }
        }


class SymbolInfo(BaseModel):
    """标的信息"""

    symbol: str = Field(..., description="标的代码 (如 BTCUSDT, 600519)")
    name: str = Field("", description="标的名称")
    market_type: MarketTypeEnum = Field(..., description="市场类型")
    exchange: str = Field("", description="交易所")
    data_source: DataSourceEnum = Field(..., description="数据源")
    base_currency: str = Field("", description="计价货币 (USDT, CNY, HKD, USD)")
    status: str = Field("trading", description="状态: trading/halted/delisted")
    # 可选的实时行情字段
    current_price: Optional[float] = Field(None, description="最新价")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    volume: Optional[float] = Field(None, description="成交量")
    turnover: Optional[float] = Field(None, description="成交额")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "600519",
                "name": "贵州茅台",
                "market_type": "cn_stock",
                "exchange": "SSE",
                "data_source": "akshare",
                "base_currency": "CNY",
                "status": "trading",
                "current_price": 1800.0,
                "change_percent": 0.84,
            }
        }


class MarketKLineData(BaseModel):
    """
    统一 K 线数据点 (兼容 TradingView UDF 格式)

    TradingView getBars 需要的字段:
    - time: Unix 时间戳 (秒)
    - open, high, low, close, volume
    """

    time: int = Field(..., description="Unix 时间戳 (秒)")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    turnover: Optional[float] = Field(None, description="成交额")


# === API 响应模型 ===

class MarketTypesResponse(BaseModel):
    """市场类型列表响应"""

    types: List[MarketType] = Field(default_factory=list, description="支持的市场类型列表")


class SymbolListResponse(BaseModel):
    """标的列表响应"""

    market_type: str = Field(..., description="市场类型")
    total: int = Field(0, description="标的总数")
    symbols: List[SymbolInfo] = Field(default_factory=list, description="标的列表")


class SymbolSearchResponse(BaseModel):
    """标的搜索响应"""

    query: str = Field(..., description="搜索关键词")
    total: int = Field(0, description="结果总数")
    symbols: List[SymbolInfo] = Field(default_factory=list, description="搜索结果")


class KLineResponse(BaseModel):
    """K 线数据响应"""

    symbol: str = Field(..., description="标的代码")
    period: str = Field(..., description="K 线周期")
    data: List[MarketKLineData] = Field(default_factory=list, description="K 线数据")
    no_data: bool = Field(False, description="是否无更多数据 (用于 TradingView 分页)")


class RealtimeQuoteItem(BaseModel):
    """实时行情条目"""

    symbol: str = Field(..., description="标的代码")
    name: str = Field("", description="标的名称")
    price: Optional[float] = Field(None, description="最新价")
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    volume: Optional[float] = Field(None, description="成交量")
    turnover: Optional[float] = Field(None, description="成交额")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    open: Optional[float] = Field(None, description="开盘价")
    prev_close: Optional[float] = Field(None, description="昨收价")
    update_time: Optional[str] = Field(None, description="更新时间")


class RealtimeResponse(BaseModel):
    """批量实时行情响应"""

    quotes: List[RealtimeQuoteItem] = Field(default_factory=list, description="行情列表")


# === 自选列表相关 ===

class WatchlistItem(BaseModel):
    """自选列表条目"""

    symbol: str = Field(..., description="标的代码")
    name: str = Field("", description="标的名称")
    market_type: str = Field("", description="市场类型")
    exchange: str = Field("", description="交易所")
    data_source: str = Field("", description="数据源")
    sort_order: int = Field(0, description="排序序号")
    added_at: Optional[float] = Field(None, description="添加时间戳")


class WatchlistResponse(BaseModel):
    """自选列表响应"""

    total: int = Field(0, description="自选总数")
    symbols: List[WatchlistItem] = Field(default_factory=list, description="自选列表")


class WatchlistAddRequest(BaseModel):
    """添加自选请求"""

    symbol: str = Field(..., description="标的代码")
    name: str = Field("", description="标的名称")
    market_type: str = Field("", description="市场类型")
    exchange: str = Field("", description="交易所")
    data_source: str = Field("", description="数据源")


class WatchlistReorderRequest(BaseModel):
    """自选排序请求"""

    symbols: List[str] = Field(..., description="按顺序排列的标的代码列表")
