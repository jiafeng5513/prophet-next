# SMA 简单移动平均线指标
# Prophet-Next 示例指标


def calculate(close_prices: list[float], period: int = 20) -> list[float]:
    """计算简单移动平均线

    Args:
        close_prices: 收盘价序列
        period: 均线周期，默认20

    Returns:
        移动平均线数值序列，前 period-1 个值为 None
    """
    result = []
    for i in range(len(close_prices)):
        if i < period - 1:
            result.append(None)
        else:
            window = close_prices[i - period + 1:i + 1]
            result.append(sum(window) / period)
    return result
