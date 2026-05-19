# -*- coding: utf-8 -*-
"""
===================================
枚举类型定义
===================================

集中管理系统中使用的枚举类型，提供类型安全和代码可读性。
"""

from enum import Enum


class MarketType(str, Enum):
    """市场类型"""
    A_SHARE = "A_SHARE"       # A股（沪深京）
    HK = "HK"                 # 港股
    US = "US"                 # 美股
    CRYPTO = "CRYPTO"         # 加密货币
    FUTURES = "FUTURES"       # 大宗商品期货
    ETF = "ETF"               # ETF 基金

    @classmethod
    def from_market_type_str(cls, value: str) -> "MarketType":
        """从 market_gateway 的 market_type 字符串转换"""
        mapping = {
            "cn_stock": cls.A_SHARE,
            "cn_etf": cls.ETF,
            "hk_stock": cls.HK,
            "us_stock": cls.US,
            "crypto": cls.CRYPTO,
            "cn_futures": cls.FUTURES,
        }
        return mapping.get(value, cls.A_SHARE)

    @property
    def display_name(self) -> str:
        return {
            MarketType.A_SHARE: "A股",
            MarketType.HK: "港股",
            MarketType.US: "美股",
            MarketType.CRYPTO: "加密货币",
            MarketType.FUTURES: "期货",
            MarketType.ETF: "ETF",
        }.get(self, "未知")


class PeriodType(str, Enum):
    """K线周期类型"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN = "1M"

    @property
    def display_name(self) -> str:
        return {
            PeriodType.M1: "1分钟",
            PeriodType.M5: "5分钟",
            PeriodType.M15: "15分钟",
            PeriodType.M30: "30分钟",
            PeriodType.H1: "1小时",
            PeriodType.H4: "4小时",
            PeriodType.D1: "日线",
            PeriodType.W1: "周线",
            PeriodType.MN: "月线",
        }.get(self, self.value)


class NewsImportance(str, Enum):
    """新闻重要性"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NewsSentimentLabel(str, Enum):
    """新闻情感标签"""
    STRONGLY_POSITIVE = "strongly_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    STRONGLY_NEGATIVE = "strongly_negative"

    @classmethod
    def from_score(cls, score: float) -> "NewsSentimentLabel":
        """从情感分数转换为标签"""
        if score >= 0.6:
            return cls.STRONGLY_POSITIVE
        elif score >= 0.2:
            return cls.POSITIVE
        elif score > -0.2:
            return cls.NEUTRAL
        elif score > -0.6:
            return cls.NEGATIVE
        else:
            return cls.STRONGLY_NEGATIVE


class ReportType(str, Enum):
    """
    报告类型枚举

    用于 API 触发分析时选择推送的报告格式。
    继承 str 使其可以直接与字符串比较和序列化。
    """
    SIMPLE = "simple"  # 精简报告：使用 generate_single_stock_report
    FULL = "full"      # 完整报告：使用 generate_dashboard_report
    BRIEF = "brief"    # 简洁模式：3-5 句话概括，适合移动端/推送

    @classmethod
    def from_str(cls, value: str) -> "ReportType":
        """
        从字符串安全地转换为枚举值
        
        Args:
            value: 字符串值
            
        Returns:
            对应的枚举值，无效输入返回默认值 SIMPLE
        """
        try:
            normalized = value.lower().strip()
            if normalized == "detailed":
                normalized = cls.FULL.value
            return cls(normalized)
        except (ValueError, AttributeError):
            return cls.SIMPLE
    
    @property
    def display_name(self) -> str:
        """获取用于显示的名称"""
        return {
            ReportType.SIMPLE: "精简报告",
            ReportType.FULL: "完整报告",
            ReportType.BRIEF: "简洁报告",
        }.get(self, "精简报告")
