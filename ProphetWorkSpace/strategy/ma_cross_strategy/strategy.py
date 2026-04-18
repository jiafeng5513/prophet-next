# 均线交叉策略
# Prophet-Next 示例策略

from indicator.sma_indicator import calculate as sma


def generate_signal(data: dict) -> str:
    """生成交易信号

    Args:
        data: 包含 OHLCV 数据的字典，至少包含 "close" 键

    Returns:
        "buy" / "sell" / "hold"
    """
    close = data.get("close", [])
    if len(close) < 21:
        return "hold"

    ma_short = sma(close, period=5)
    ma_long = sma(close, period=20)

    if ma_short[-1] is None or ma_long[-1] is None:
        return "hold"
    if ma_short[-2] is None or ma_long[-2] is None:
        return "hold"

    # 短期均线上穿长期均线 -> 买入
    if ma_short[-1] > ma_long[-1] and ma_short[-2] <= ma_long[-2]:
        return "buy"
    # 短期均线下穿长期均线 -> 卖出
    elif ma_short[-1] < ma_long[-1] and ma_short[-2] >= ma_long[-2]:
        return "sell"

    return "hold"
