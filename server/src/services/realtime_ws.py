# -*- coding: utf-8 -*-
"""
===================================
WebSocket 实时行情中继服务 (Realtime WS Relay)
===================================

职责:
1. 后端连接 TickFlow WebSocket (上游), 持有 API Key (安全)
2. 前端通过本地 WebSocket ws://127.0.0.1:8100/ws/market 订阅
3. 多前端页面共享一条上游连接, 减少 API 配额消耗
4. 自动重连 + 订阅恢复
5. 不持有 API Key 的情况下, 降级为 REST 轮询模式

协议:
  前端 → 后端:
    {"op": "subscribe", "channel": "quotes", "symbols": ["600519", "000001"]}
    {"op": "unsubscribe", "channel": "quotes", "symbols": ["600519"]}
    {"op": "subscribe", "channel": "depth", "symbols": ["600519"]}
    {"op": "ping"}

  后端 → 前端:
    {"op": "quotes", "data": [{ symbol, name, price, change, ... }]}
    {"op": "depth", "data": { symbol, bids: [...], asks: [...] }}
    {"op": "pong"}
    {"op": "error", "message": "..."}
    {"op": "status", "upstream": "connected" | "disconnected" | "polling"}
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class RealtimeWSRelay:
    """WebSocket 实时行情中继服务 (单例)"""

    _instance: Optional["RealtimeWSRelay"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 前端客户端管理
        self._clients: Set[WebSocket] = set()
        # 每个客户端的订阅: {ws: {"quotes": set(...), "depth": set(...)}}
        self._subscriptions: Dict[WebSocket, Dict[str, Set[str]]] = {}

        # 聚合订阅 (所有客户端的并集)
        self._aggregated_quotes: Set[str] = set()
        self._aggregated_depth: Set[str] = set()

        # 上游 TickFlow WebSocket 状态
        self._upstream_ws = None
        self._upstream_task: Optional[asyncio.Task] = None
        self._upstream_connected = False
        self._reconnect_delay = 1.0

        # 轮询 fallback
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_interval = 5.0  # 5 秒轮询

        # 配置
        self._api_key = os.environ.get("TICKFLOW_API_KEY", "")
        self._upstream_url = "wss://api.tickflow.org/v1/ws/stream"

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key.strip())

    @property
    def mode(self) -> str:
        """当前工作模式: websocket / polling / idle"""
        if self._upstream_connected:
            return "websocket"
        if self._polling_task and not self._polling_task.done():
            return "polling"
        return "idle"

    def reload_config(self):
        """重新加载配置 (API Key 变更后调用)"""
        new_key = os.environ.get("TICKFLOW_API_KEY", "")
        if new_key != self._api_key:
            self._api_key = new_key
            logger.info("[RealtimeWS] API Key 已更新, 重连上游")
            # 触发重连
            asyncio.ensure_future(self._reconnect_upstream())

    # ==================== 前端 WebSocket 管理 ====================

    async def handle_client(self, ws: WebSocket):
        """处理一个前端 WebSocket 连接"""
        await ws.accept()
        self._clients.add(ws)
        self._subscriptions[ws] = {"quotes": set(), "depth": set()}
        logger.info("[RealtimeWS] 新客户端连接, 当前 %d 个", len(self._clients))

        # 通知客户端当前上游状态
        await self._send_to_client(ws, {
            "op": "status",
            "upstream": self.mode,
        })

        try:
            while True:
                raw = await ws.receive_text()
                await self._handle_client_message(ws, raw)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("[RealtimeWS] 客户端异常: %s", e)
        finally:
            await self._remove_client(ws)

    async def _handle_client_message(self, ws: WebSocket, raw: str):
        """处理前端发来的消息"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_to_client(ws, {"op": "error", "message": "无效 JSON"})
            return

        op = msg.get("op", "")

        if op == "ping":
            await self._send_to_client(ws, {"op": "pong"})
            return

        if op == "subscribe":
            channel = msg.get("channel", "quotes")
            symbols = msg.get("symbols", [])
            if not isinstance(symbols, list):
                symbols = [symbols]
            self._subscriptions[ws].setdefault(channel, set()).update(symbols)
            await self._update_aggregated_subscriptions()
            return

        if op == "unsubscribe":
            channel = msg.get("channel", "quotes")
            symbols = msg.get("symbols", [])
            if not isinstance(symbols, list):
                symbols = [symbols]
            sub_set = self._subscriptions[ws].get(channel, set())
            for s in symbols:
                sub_set.discard(s)
            await self._update_aggregated_subscriptions()
            return

        await self._send_to_client(ws, {"op": "error", "message": f"未知操作: {op}"})

    async def _remove_client(self, ws: WebSocket):
        """移除一个客户端连接"""
        self._clients.discard(ws)
        self._subscriptions.pop(ws, None)
        logger.info("[RealtimeWS] 客户端断开, 剩余 %d 个", len(self._clients))
        await self._update_aggregated_subscriptions()

    # ==================== 聚合订阅管理 ====================

    async def _update_aggregated_subscriptions(self):
        """重新计算聚合订阅 (所有客户端的并集)"""
        new_quotes: Set[str] = set()
        new_depth: Set[str] = set()

        for subs in self._subscriptions.values():
            new_quotes.update(subs.get("quotes", set()))
            new_depth.update(subs.get("depth", set()))

        added_quotes = new_quotes - self._aggregated_quotes
        removed_quotes = self._aggregated_quotes - new_quotes
        added_depth = new_depth - self._aggregated_depth
        removed_depth = self._aggregated_depth - new_depth

        self._aggregated_quotes = new_quotes
        self._aggregated_depth = new_depth

        # 通知上游订阅变更
        if self._upstream_connected:
            if added_quotes:
                await self._upstream_subscribe("quotes", list(added_quotes))
            if removed_quotes:
                await self._upstream_unsubscribe("quotes", list(removed_quotes))
            if added_depth:
                await self._upstream_subscribe("depth", list(added_depth))
            if removed_depth:
                await self._upstream_unsubscribe("depth", list(removed_depth))

        # 无客户端时停止轮询; 有客户端但无上游时启动轮询
        if not self._aggregated_quotes and not self._aggregated_depth:
            self._stop_polling()
            if self._upstream_task and not self._upstream_task.done():
                self._upstream_task.cancel()
        elif not self._upstream_connected:
            self._ensure_polling()
            # 也尝试连接上游
            self._ensure_upstream()

    # ==================== 上游 TickFlow WebSocket ====================

    def _ensure_upstream(self):
        """确保上游连接任务在运行"""
        if not self.has_api_key:
            return  # 无 API Key 则只走轮询
        if self._upstream_task is None or self._upstream_task.done():
            self._upstream_task = asyncio.ensure_future(self._upstream_loop())

    async def _upstream_loop(self):
        """上游 WebSocket 连接循环 (自动重连)"""
        while self._aggregated_quotes or self._aggregated_depth:
            try:
                await self._connect_upstream()
            except asyncio.CancelledError:
                break
            except (AttributeError, RuntimeError) as e:
                # websockets 14+ cleanup bug: 'ClientConnection' has no attribute 'recv_messages'
                logger.debug("[RealtimeWS] 上游清理异常 (已忽略): %s", e)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)
            except Exception as e:
                logger.warning("[RealtimeWS] 上游连接失败: %s, %s秒后重试",
                               e, self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def _connect_upstream(self):
        """建立上游 TickFlow WebSocket 连接"""
        import websockets

        url = f"{self._upstream_url}?api_key={self._api_key}"
        logger.info("[RealtimeWS] 连接上游 TickFlow WebSocket...")

        async with websockets.connect(
            url, ping_interval=25, ping_timeout=10, open_timeout=15,
            close_timeout=5,
        ) as ws:
            self._upstream_ws = ws
            self._upstream_connected = True
            self._reconnect_delay = 1.0
            logger.info("[RealtimeWS] 上游连接成功")
            self._stop_polling()  # 上游连通后停止轮询

            # 通知所有前端客户端
            await self._broadcast({"op": "status", "upstream": "websocket"})

            # 重新订阅所有聚合的标的
            if self._aggregated_quotes:
                await self._upstream_subscribe("quotes", list(self._aggregated_quotes))
            if self._aggregated_depth:
                await self._upstream_subscribe("depth", list(self._aggregated_depth))

            # 接收消息循环
            try:
                async for raw in ws:
                    await self._handle_upstream_message(raw)
            except websockets.ConnectionClosed as e:
                logger.warning("[RealtimeWS] 上游连接关闭: %s", e)
            finally:
                self._upstream_connected = False
                self._upstream_ws = None
                await self._broadcast({"op": "status", "upstream": "disconnected"})
                # 恢复轮询
                if self._aggregated_quotes or self._aggregated_depth:
                    self._ensure_polling()

    async def _reconnect_upstream(self):
        """强制重连上游"""
        if self._upstream_ws:
            await self._upstream_ws.close()
        if self._upstream_task and not self._upstream_task.done():
            self._upstream_task.cancel()
        self._ensure_upstream()

    async def _upstream_subscribe(self, channel: str, symbols: List[str]):
        """向上游发送订阅消息"""
        if not self._upstream_ws:
            return
        from src.services.tickflow_symbol import to_tickflow_symbol
        tf_symbols = [to_tickflow_symbol(s) for s in symbols]
        msg = json.dumps({"op": "subscribe", "channel": channel, "symbols": tf_symbols})
        try:
            await self._upstream_ws.send(msg)
            logger.debug("[RealtimeWS] 上游订阅 %s: %s", channel, tf_symbols)
        except Exception as e:
            logger.warning("[RealtimeWS] 上游发送失败: %s", e)

    async def _upstream_unsubscribe(self, channel: str, symbols: List[str]):
        """向上游发送退订消息"""
        if not self._upstream_ws:
            return
        from src.services.tickflow_symbol import to_tickflow_symbol
        tf_symbols = [to_tickflow_symbol(s) for s in symbols]
        msg = json.dumps({"op": "unsubscribe", "channel": channel, "symbols": tf_symbols})
        try:
            await self._upstream_ws.send(msg)
        except Exception:
            pass

    async def _handle_upstream_message(self, raw: str):
        """处理上游推送的消息, 转发给前端"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        op = msg.get("op", "")

        if op == "quotes":
            data = msg.get("data", [])
            normalized = self._normalize_quotes(data)
            await self._dispatch_quotes(normalized)

        elif op == "depth":
            data = msg.get("data", {})
            normalized = self._normalize_depth(data)
            await self._dispatch_depth(normalized)

        # TickFlow ping/pong 由 websockets 库自动处理

    def _normalize_quotes(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将 TickFlow 行情格式转为前端统一格式"""
        from src.services.tickflow_symbol import from_tickflow_symbol

        results = []
        for q in data:
            if not q:
                continue
            tf_sym = str(q.get("symbol", ""))
            code = from_tickflow_symbol(tf_sym)
            ext = q.get("ext") or {}
            change_pct = ext.get("change_pct")
            if change_pct is not None:
                try:
                    change_pct = float(change_pct) * 100  # 比例 → 百分比
                except (TypeError, ValueError):
                    change_pct = None
            results.append({
                "symbol": code,
                "name": ext.get("name") or q.get("name") or "",
                "price": q.get("last_price"),
                "change": ext.get("change_amount"),
                "change_percent": change_pct,
                "volume": q.get("volume"),
                "turnover": q.get("amount"),
                "high": q.get("high"),
                "low": q.get("low"),
                "open": q.get("open"),
                "prev_close": q.get("prev_close"),
                "timestamp": q.get("timestamp"),
            })
        return results

    def _normalize_depth(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """将 TickFlow 五档盘口转为前端格式"""
        from src.services.tickflow_symbol import from_tickflow_symbol

        tf_sym = str(data.get("symbol", ""))
        return {
            "symbol": from_tickflow_symbol(tf_sym),
            "bids": data.get("bids", []),  # [[price, volume], ...]
            "asks": data.get("asks", []),
            "timestamp": data.get("timestamp"),
        }

    async def _dispatch_quotes(self, quotes: List[Dict[str, Any]]):
        """将行情数据分发给已订阅的前端客户端"""
        if not quotes:
            return
        # 构建 symbol → quote 索引
        quote_map: Dict[str, Dict] = {q["symbol"]: q for q in quotes}

        for ws, subs in list(self._subscriptions.items()):
            sub_symbols = subs.get("quotes", set())
            if not sub_symbols:
                continue
            # 过滤出该客户端关心的
            client_quotes = [quote_map[s] for s in sub_symbols if s in quote_map]
            if client_quotes:
                await self._send_to_client(ws, {"op": "quotes", "data": client_quotes})

    async def _dispatch_depth(self, depth: Dict[str, Any]):
        """将五档数据分发给已订阅的前端客户端"""
        symbol = depth.get("symbol", "")
        if not symbol:
            return
        for ws, subs in list(self._subscriptions.items()):
            if symbol in subs.get("depth", set()):
                await self._send_to_client(ws, {"op": "depth", "data": depth})

    # ==================== REST 轮询 Fallback ====================

    def _ensure_polling(self):
        """确保轮询任务在运行"""
        if self._polling_task is None or self._polling_task.done():
            self._polling_task = asyncio.ensure_future(self._polling_loop())

    def _stop_polling(self):
        """停止轮询"""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()

    async def _polling_loop(self):
        """REST 轮询循环: 定期获取行情并推送"""
        logger.info("[RealtimeWS] 进入 REST 轮询模式 (间隔 %.1fs)", self._polling_interval)
        await self._broadcast({"op": "status", "upstream": "polling"})

        try:
            while True:
                await self._poll_once()
                await asyncio.sleep(self._polling_interval)
        except asyncio.CancelledError:
            logger.info("[RealtimeWS] 轮询已停止")

    async def _poll_once(self):
        """执行一次 REST 轮询"""
        if not self._aggregated_quotes:
            return

        symbols_list = list(self._aggregated_quotes)
        try:
            from src.services.market_gateway import MarketGateway
            gateway = MarketGateway()
            quotes = gateway.get_realtime_quotes(symbols_list)
            if quotes:
                await self._dispatch_quotes(quotes)
        except Exception as e:
            logger.warning("[RealtimeWS] 轮询失败: %s", e)

    # ==================== 工具方法 ====================

    async def _send_to_client(self, ws: WebSocket, data: dict):
        """安全地发送消息给客户端"""
        try:
            await ws.send_json(data)
        except Exception:
            # 客户端可能已断开
            pass

    async def _broadcast(self, data: dict):
        """广播消息给所有客户端"""
        for ws in list(self._clients):
            await self._send_to_client(ws, data)

    def get_status(self) -> Dict[str, Any]:
        """获取中继服务状态"""
        return {
            "mode": self.mode,
            "has_api_key": self.has_api_key,
            "clients": len(self._clients),
            "subscribed_quotes": list(self._aggregated_quotes),
            "subscribed_depth": list(self._aggregated_depth),
            "upstream_connected": self._upstream_connected,
        }
