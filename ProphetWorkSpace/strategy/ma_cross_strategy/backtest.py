# 均线交叉策略回测脚本

from strategy import generate_signal


def run_backtest(prices: list[float]) -> dict:
    """简单回测框架

    Args:
        prices: 历史收盘价序列

    Returns:
        回测结果统计
    """
    position = 0  # 0: 空仓, 1: 持仓
    trades = []
    entry_price = 0.0

    for i in range(1, len(prices)):
        data = {"close": prices[:i + 1]}
        signal = generate_signal(data)

        if signal == "buy" and position == 0:
            position = 1
            entry_price = prices[i]
            trades.append({"type": "buy", "price": entry_price, "index": i})
        elif signal == "sell" and position == 1:
            position = 0
            profit = prices[i] - entry_price
            trades.append({"type": "sell", "price": prices[i], "index": i, "profit": profit})

    return {
        "total_trades": len(trades),
        "trades": trades
    }


if __name__ == "__main__":
    test_prices = [10, 11, 12, 11, 13, 14, 15, 14, 13, 12,
                   11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                   21, 22, 21, 20, 19, 18, 19, 20, 21, 22]
    result = run_backtest(test_prices)
    print(f"总交易次数: {result['total_trades']}")
    for t in result["trades"]:
        print(t)
