# -*- coding: utf-8 -*-
"""
TickFlow 标的代码转换工具

内部代码 ↔ TickFlow 代码格式转换：
- 600519  ↔ 600519.SH  (上交所)
- 000001  ↔ 000001.SZ  (深交所)
- 920748  ↔ 920748.BJ  (北交所)
- HK00700 ↔ 00700.HK   (港股)
- AAPL    ↔ AAPL.US     (美股)
"""


def to_tickflow_symbol(code: str) -> str:
    """内部代码 → TickFlow 格式 (如 600519 → 600519.SH)"""
    c = (code or "").strip()
    if not c:
        return c

    upper = c.upper()

    # 已经是 TickFlow 格式 (含 .)
    if "." in c:
        return upper

    # 港股: HK00700 → 00700.HK
    if upper.startswith("HK") and upper[2:].isdigit():
        digits = upper[2:]
        return f"{digits}.HK"

    # 6 位纯数字 → A 股 / ETF / 北交所
    if c.isdigit() and len(c) == 6:
        # 北交所: 43xxxx, 83xxxx, 87xxxx, 88xxxx, 92xxxx
        if c.startswith(("43", "83", "87", "88", "92")):
            return f"{c}.BJ"
        if c.startswith(("6", "9")):
            return f"{c}.SH"
        if c.startswith(("0", "1", "2", "3")):
            return f"{c}.SZ"
        if c.startswith(("4", "8")):
            return f"{c}.BJ"
        return f"{c}.SH"

    # 纯字母 → 美股
    if c.isalpha():
        return f"{upper}.US"

    return upper


def from_tickflow_symbol(tf_symbol: str) -> str:
    """TickFlow 格式 → 内部代码 (如 600519.SH → 600519)"""
    s = (tf_symbol or "").strip()
    if not s or "." not in s:
        return s

    base, suffix = s.rsplit(".", 1)
    suffix = suffix.upper()

    if suffix in ("SH", "SZ", "BJ"):
        return base
    if suffix == "HK":
        return f"HK{base.zfill(5)}"
    if suffix == "US":
        return base.upper()

    return s


# TickFlow 标的池 ID 映射
UNIVERSE_MAP = {
    "cn_stock": "CN_Equity_A",
    "cn_etf": "CN_ETF",
    "cn_index": "CN_Index",
    "us_stock": "US_Equity",
    "hk_stock": "HK_Equity",
}

# TickFlow K 线周期映射 (内部周期 → TickFlow 周期)
PERIOD_MAP = {
    "1": "1m",
    "1m": "1m",
    "5": "5m",
    "5m": "5m",
    "10": "10m",
    "10m": "10m",
    "15": "15m",
    "15m": "15m",
    "30": "30m",
    "30m": "30m",
    "60": "60m",
    "60m": "60m",
    "1h": "60m",
    "1H": "60m",
    "4h": "60m",  # TickFlow 无 4h, 需要在应用层聚合或回退
    "4H": "60m",
    "1d": "1d",
    "1D": "1d",
    "1w": "1w",
    "1W": "1w",
    "1M": "1M",
}
