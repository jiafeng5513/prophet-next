# -*- coding: utf-8 -*-
"""
===================================
Binance WebSocket 实时行情客户端
===================================

功能：
1. 实时K线推送 (<symbol>@kline_<interval>)
2. 实时行情Ticker推送 (<symbol>@ticker)
3. 自动重连 (24h连接刷新、网络断线)
4. 心跳管理 (ping/pong)

WebSocket地址：
- wss://stream.binance.com:9443/ws/<streamName>
- wss://stream.binance.com:9443/stream?streams=<s1>/<s2> (合并流)
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Set, Callable, Any, List

logger = logging.getLogger(__name__)

# 常量
WS_BASE_URL = "wss://stream.binance.com:9443"
WS_SINGLE_STREAM = f"{WS_BASE_URL}/ws"
WS_COMBINED_STREAM = f"{WS_BASE_URL}/stream"
MAX_STREAMS_PER_CONNECTION = 1024
CONNECTION_LIFETIME = 23 * 3600  # 23小时（提前1小时刷新，避免24h强制断连）
RECONNECT_DELAY_BASE = 1.0
RECONNECT_DELAY_MAX = 60.0
PING_INTERVAL = 180  # 3分钟发送一次ping


class BinanceWSClient:
    """
    Binance WebSocket 实时行情客户端。

    支持动态订阅/取消订阅，自动重连。
    使用asyncio实现非阻塞IO。
    """

    def __init__(self, proxy: Optional[str] = None,
                 on_kline: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_ticker: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Args:
            proxy: WebSocket代理URL
            on_kline: K线回调函数
            on_ticker: Ticker回调函数
        """
        self._proxy = proxy
        self._on_kline = on_kline
        self._on_ticker = on_ticker

        self._subscriptions: Set[str] = set()
        self._ws = None
        self._running = False
        self._connected = False
        self._connect_time = 0.0
        self._reconnect_count = 0
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> Set[str]:
        return self._subscriptions.copy()

    async def start(self):
        """启动WebSocket连接"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[BinanceWS] 客户端已启动")

    async def stop(self):
        """停止WebSocket连接"""
        self._running = False
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
        logger.info("[BinanceWS] 客户端已停止")

    async def subscribe_kline(self, symbol: str, interval: str = "1m"):
        """订阅K线流"""
        stream = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe([stream])

    async def unsubscribe_kline(self, symbol: str, interval: str = "1m"):
        """取消订阅K线流"""
        stream = f"{symbol.lower()}@kline_{interval}"
        await self._unsubscribe([stream])

    async def subscribe_ticker(self, symbol: str):
        """订阅24h Ticker流"""
        stream = f"{symbol.lower()}@ticker"
        await self._subscribe([stream])

    async def unsubscribe_ticker(self, symbol: str):
        """取消订阅Ticker流"""
        stream = f"{symbol.lower()}@ticker"
        await self._unsubscribe([stream])

    async def _subscribe(self, streams: List[str]):
        """发送订阅请求"""
        new_streams = [s for s in streams if s not in self._subscriptions]
        if not new_streams:
            return

        self._subscriptions.update(new_streams)

        if self._ws and self._connected:
            msg = {
                "method": "SUBSCRIBE",
                "params": new_streams,
                "id": int(time.time() * 1000),
            }
            try:
                await self._ws.send(json.dumps(msg))
                logger.debug(f"[BinanceWS] 已订阅: {new_streams}")
            except Exception as e:
                logger.warning(f"[BinanceWS] 订阅发送失败: {e}")

    async def _unsubscribe(self, streams: List[str]):
        """发送取消订阅请求"""
        existing = [s for s in streams if s in self._subscriptions]
        if not existing:
            return

        self._subscriptions.difference_update(existing)

        if self._ws and self._connected:
            msg = {
                "method": "UNSUBSCRIBE",
                "params": existing,
                "id": int(time.time() * 1000),
            }
            try:
                await self._ws.send(json.dumps(msg))
                logger.debug(f"[BinanceWS] 已取消订阅: {existing}")
            except Exception as e:
                logger.warning(f"[BinanceWS] 取消订阅发送失败: {e}")

    async def _run_loop(self):
        """WebSocket主循环：连接、接收消息、自动重连"""
        try:
            import websockets
        except ImportError:
            logger.error("[BinanceWS] 需要安装 websockets 库: pip install websockets")
            return

        while self._running:
            try:
                await self._connect_and_listen(websockets)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[BinanceWS] 连接异常: {e}")

            if not self._running:
                break

            # 指数退避重连
            delay = min(
                RECONNECT_DELAY_BASE * (2 ** self._reconnect_count),
                RECONNECT_DELAY_MAX,
            )
            self._reconnect_count += 1
            logger.info(f"[BinanceWS] {delay:.1f}s 后重连 (第{self._reconnect_count}次)")
            await asyncio.sleep(delay)

    async def _connect_and_listen(self, websockets_module):
        """建立连接并监听消息"""
        url = WS_SINGLE_STREAM
        connect_kwargs = {}
        if self._proxy:
            # websockets库不直接支持proxy，需通过环境变量或第三方库
            pass

        async with websockets_module.connect(
            url,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=5,
            **connect_kwargs,
        ) as ws:
            self._ws = ws
            self._connected = True
            self._connect_time = time.time()
            self._reconnect_count = 0
            logger.info("[BinanceWS] 已连接")

            # 重新订阅所有流
            if self._subscriptions:
                msg = {
                    "method": "SUBSCRIBE",
                    "params": list(self._subscriptions),
                    "id": int(time.time() * 1000),
                }
                await ws.send(json.dumps(msg))
                logger.info(f"[BinanceWS] 重新订阅 {len(self._subscriptions)} 个流")

            # 消息接收循环
            try:
                async for raw_msg in ws:
                    if not self._running:
                        break

                    # 检查连接是否需要刷新（23h）
                    if time.time() - self._connect_time > CONNECTION_LIFETIME:
                        logger.info("[BinanceWS] 连接已达生命周期，主动断开重连")
                        break

                    self._handle_message(raw_msg)
            except websockets_module.exceptions.ConnectionClosed as e:
                logger.info(f"[BinanceWS] 连接关闭: code={e.code} reason={e.reason}")
            finally:
                self._connected = False
                self._ws = None

    def _handle_message(self, raw_msg: str):
        """解析并分发WebSocket消息"""
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        # 订阅确认消息
        if "result" in data and "id" in data:
            return

        # 合并流消息格式
        if "stream" in data and "data" in data:
            data = data["data"]

        event_type = data.get("e")

        if event_type == "kline":
            self._handle_kline(data)
        elif event_type == "24hrTicker":
            self._handle_ticker(data)

    def _handle_kline(self, data: Dict[str, Any]):
        """处理K线消息"""
        k = data.get("k", {})
        kline_data = {
            "symbol": data.get("s", ""),
            "interval": k.get("i", ""),
            "open_time": k.get("t"),
            "close_time": k.get("T"),
            "open": float(k.get("o", 0)),
            "high": float(k.get("h", 0)),
            "low": float(k.get("l", 0)),
            "close": float(k.get("c", 0)),
            "volume": float(k.get("v", 0)),
            "quote_volume": float(k.get("q", 0)),
            "trades": int(k.get("n", 0)),
            "is_closed": k.get("x", False),
            "event_time": data.get("E"),
        }

        if self._on_kline:
            try:
                self._on_kline(kline_data)
            except Exception as e:
                logger.warning(f"[BinanceWS] K线回调异常: {e}")

    def _handle_ticker(self, data: Dict[str, Any]):
        """处理Ticker消息"""
        ticker_data = {
            "symbol": data.get("s", ""),
            "price_change": float(data.get("p", 0)),
            "price_change_pct": float(data.get("P", 0)),
            "last_price": float(data.get("c", 0)),
            "open_price": float(data.get("o", 0)),
            "high_price": float(data.get("h", 0)),
            "low_price": float(data.get("l", 0)),
            "volume": float(data.get("v", 0)),
            "quote_volume": float(data.get("q", 0)),
            "event_time": data.get("E"),
        }

        if self._on_ticker:
            try:
                self._on_ticker(ticker_data)
            except Exception as e:
                logger.warning(f"[BinanceWS] Ticker回调异常: {e}")
