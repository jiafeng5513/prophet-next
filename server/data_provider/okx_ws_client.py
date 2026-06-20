# -*- coding: utf-8 -*-
"""
===================================
OKX WebSocket 实时行情客户端
===================================

功能：
1. 实时K线推送 (candle<period> channel)
2. 实时行情Ticker推送 (tickers channel)
3. 自动重连与心跳管理

WebSocket地址：
- 公开频道: wss://ws.okx.com:8443/ws/v5/public
- AWS: wss://wsaws.okx.com:8443/ws/v5/public
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Set, Callable, Any, List, Tuple

logger = logging.getLogger(__name__)

# 常量
WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
WS_PUBLIC_URL_AWS = "wss://wsaws.okx.com:8443/ws/v5/public"
PING_INTERVAL = 25  # OKX要求30s内发送ping
RECONNECT_DELAY_BASE = 1.0
RECONNECT_DELAY_MAX = 60.0


class OKXWSClient:
    """
    OKX WebSocket 公开频道客户端。

    支持动态订阅/取消订阅K线和Ticker。
    使用asyncio实现非阻塞IO。
    """

    def __init__(self, proxy: Optional[str] = None, use_aws: bool = False,
                 on_kline: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_ticker: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Args:
            proxy: WebSocket代理URL
            use_aws: 是否使用AWS节点
            on_kline: K线回调函数
            on_ticker: Ticker回调函数
        """
        self._ws_url = WS_PUBLIC_URL_AWS if use_aws else WS_PUBLIC_URL
        self._proxy = proxy
        self._on_kline = on_kline
        self._on_ticker = on_ticker

        self._subscriptions: List[Dict[str, str]] = []  # OKX订阅参数列表
        self._ws = None
        self._running = False
        self._connected = False
        self._reconnect_count = 0
        self._task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self):
        """启动WebSocket连接"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[OKX_WS] 客户端已启动")

    async def stop(self):
        """停止WebSocket连接"""
        self._running = False
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("[OKX_WS] 客户端已停止")

    async def subscribe_kline(self, inst_id: str, period: str = "1m"):
        """
        订阅K线频道。

        Args:
            inst_id: 交易对ID，如 'BTC-USDT'
            period: 周期，如 '1m', '5m', '1H', '1D'
        """
        channel = f"candle{period}"
        arg = {"channel": channel, "instId": inst_id}
        await self._subscribe([arg])

    async def unsubscribe_kline(self, inst_id: str, period: str = "1m"):
        """取消订阅K线频道"""
        channel = f"candle{period}"
        arg = {"channel": channel, "instId": inst_id}
        await self._unsubscribe([arg])

    async def subscribe_ticker(self, inst_id: str):
        """订阅Ticker频道"""
        arg = {"channel": "tickers", "instId": inst_id}
        await self._subscribe([arg])

    async def unsubscribe_ticker(self, inst_id: str):
        """取消订阅Ticker频道"""
        arg = {"channel": "tickers", "instId": inst_id}
        await self._unsubscribe([arg])

    async def _subscribe(self, args: List[Dict[str, str]]):
        """发送订阅请求"""
        new_args = [a for a in args if a not in self._subscriptions]
        if not new_args:
            return

        self._subscriptions.extend(new_args)

        if self._ws and self._connected:
            msg = {"op": "subscribe", "args": new_args}
            try:
                await self._ws.send(json.dumps(msg))
                logger.debug(f"[OKX_WS] 已订阅: {new_args}")
            except Exception as e:
                logger.warning(f"[OKX_WS] 订阅发送失败: {e}")

    async def _unsubscribe(self, args: List[Dict[str, str]]):
        """发送取消订阅请求"""
        existing = [a for a in args if a in self._subscriptions]
        if not existing:
            return

        for a in existing:
            self._subscriptions.remove(a)

        if self._ws and self._connected:
            msg = {"op": "unsubscribe", "args": existing}
            try:
                await self._ws.send(json.dumps(msg))
                logger.debug(f"[OKX_WS] 已取消订阅: {existing}")
            except Exception as e:
                logger.warning(f"[OKX_WS] 取消订阅发送失败: {e}")

    async def _run_loop(self):
        """WebSocket主循环"""
        try:
            import websockets
        except ImportError:
            logger.error("[OKX_WS] 需要安装 websockets 库: pip install websockets")
            return

        while self._running:
            try:
                await self._connect_and_listen(websockets)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[OKX_WS] 连接异常: {e}")

            if not self._running:
                break

            delay = min(
                RECONNECT_DELAY_BASE * (2 ** self._reconnect_count),
                RECONNECT_DELAY_MAX,
            )
            self._reconnect_count += 1
            logger.info(f"[OKX_WS] {delay:.1f}s 后重连 (第{self._reconnect_count}次)")
            await asyncio.sleep(delay)

    async def _connect_and_listen(self, websockets_module):
        """建立连接并监听消息"""
        async with websockets_module.connect(
            self._ws_url,
            ping_interval=None,  # 我们自己管理心跳
            ping_timeout=None,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._connected = True
            self._reconnect_count = 0
            logger.info("[OKX_WS] 已连接")

            # 启动心跳任务
            self._ping_task = asyncio.create_task(self._ping_loop(ws))

            # 重新订阅
            if self._subscriptions:
                msg = {"op": "subscribe", "args": self._subscriptions}
                await ws.send(json.dumps(msg))
                logger.info(f"[OKX_WS] 重新订阅 {len(self._subscriptions)} 个频道")

            # 消息接收循环
            try:
                async for raw_msg in ws:
                    if not self._running:
                        break
                    self._handle_message(raw_msg)
            except websockets_module.exceptions.ConnectionClosed as e:
                logger.info(f"[OKX_WS] 连接关闭: code={e.code} reason={e.reason}")
            finally:
                self._connected = False
                self._ws = None
                if self._ping_task:
                    self._ping_task.cancel()

    async def _ping_loop(self, ws):
        """定期发送ping保持连接"""
        try:
            while self._running and self._connected:
                await asyncio.sleep(PING_INTERVAL)
                if ws and self._connected:
                    try:
                        await ws.send("ping")
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    def _handle_message(self, raw_msg: str):
        """解析并分发消息"""
        # OKX的pong响应
        if raw_msg == "pong":
            return

        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        # 订阅确认/错误消息
        event = data.get("event")
        if event in ("subscribe", "unsubscribe", "error"):
            if event == "error":
                logger.warning(f"[OKX_WS] 错误: {data.get('msg', '')}")
            return

        # 数据推送
        arg = data.get("arg", {})
        channel = arg.get("channel", "")
        candle_data = data.get("data", [])

        if channel.startswith("candle"):
            self._handle_kline(arg, candle_data)
        elif channel == "tickers":
            self._handle_ticker(candle_data)

    def _handle_kline(self, arg: Dict[str, str], candles: List):
        """处理K线推送"""
        inst_id = arg.get("instId", "")
        channel = arg.get("channel", "")
        # 从channel名称提取周期: candle1m -> 1m
        period = channel.replace("candle", "")

        for candle in candles:
            # candle格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            if len(candle) < 9:
                continue

            kline_data = {
                "symbol": inst_id,
                "interval": period,
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "quote_volume": float(candle[7]) if candle[7] else 0.0,
                "is_closed": candle[8] == "1",
            }

            if self._on_kline:
                try:
                    self._on_kline(kline_data)
                except Exception as e:
                    logger.warning(f"[OKX_WS] K线回调异常: {e}")

    def _handle_ticker(self, tickers: List):
        """处理Ticker推送"""
        for ticker in tickers:
            if not isinstance(ticker, dict):
                continue

            ticker_data = {
                "symbol": ticker.get("instId", ""),
                "last_price": float(ticker.get("last", 0)),
                "open_price": float(ticker.get("open24h", 0)),
                "high_price": float(ticker.get("high24h", 0)),
                "low_price": float(ticker.get("low24h", 0)),
                "volume": float(ticker.get("vol24h", 0)),
                "quote_volume": float(ticker.get("volCcy24h", 0)),
                "timestamp": int(ticker.get("ts", 0)),
            }

            # 计算涨跌幅
            if ticker_data["open_price"] > 0:
                ticker_data["price_change_pct"] = (
                    (ticker_data["last_price"] - ticker_data["open_price"])
                    / ticker_data["open_price"] * 100
                )
            else:
                ticker_data["price_change_pct"] = 0.0

            if self._on_ticker:
                try:
                    self._on_ticker(ticker_data)
                except Exception as e:
                    logger.warning(f"[OKX_WS] Ticker回调异常: {e}")
