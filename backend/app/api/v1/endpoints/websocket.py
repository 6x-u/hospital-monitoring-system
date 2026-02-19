"""
WebSocket endpoint for real-time dashboard updates.
Streams live metrics, alerts, and system events to connected clients.
Developed by: MERO:TG@QP4RM
"""

import asyncio
import json
import uuid
from typing import Dict, Set

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app.core.security import JWTHandler
from app.db.redis_client import redis_client

logger = structlog.get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """
    Manages active WebSocket connections with room support.
    Allows targeted broadcasting to specific rooms (e.g., per-device).
    """

    def __init__(self) -> None:
        # user_id → set of WebSocket connections
        self._active: Dict[str, Set[WebSocket]] = {}
        # room_name → set of user_ids
        self._rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self._active:
            self._active[user_id] = set()
        self._active[user_id].add(websocket)
        logger.info("WebSocket connected", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a disconnected WebSocket."""
        if user_id in self._active:
            self._active[user_id].discard(websocket)
            if not self._active[user_id]:
                del self._active[user_id]
        for room_name, user_ids in list(self._rooms.items()):
            user_ids.discard(user_id)
        logger.info("WebSocket disconnected", user_id=user_id)

    def join_room(self, room_name: str, user_id: str) -> None:
        """Add a user to a named room for targeted broadcasts."""
        if room_name not in self._rooms:
            self._rooms[room_name] = set()
        self._rooms[room_name].add(user_id)

    async def broadcast_to_room(self, room_name: str, message: dict) -> None:
        """Send a message to all users in a room."""
        user_ids = self._rooms.get(room_name, set())
        payload = json.dumps(message)
        for user_id in user_ids:
            for ws in list(self._active.get(user_id, [])):
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

    async def broadcast_all(self, message: dict) -> None:
        """Send a message to all connected users."""
        payload = json.dumps(message)
        for user_id, connections in list(self._active.items()):
            for ws in list(connections):
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

    @property
    def active_connection_count(self) -> int:
        return sum(len(c) for c in self._active.values())


manager = ConnectionManager()


async def _authenticate_ws(token: str) -> dict:
    """Validate JWT from WebSocket query parameter."""
    try:
        payload = await JWTHandler.decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload
    except (JWTError, ValueError, Exception) as exc:
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str = "") -> None:
    """
    Primary WebSocket endpoint for real-time dashboard updates.
    Clients must pass a valid JWT as ?token= query parameter.
    Streams: live metrics, alerts, system events.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = await _authenticate_ws(token)
    except WebSocketDisconnect:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["sub"]
    await manager.connect(websocket, user_id)

    # Subscribe to Redis pub/sub channels for live data
    pubsub = redis_client._get_client().pubsub()
    await pubsub.subscribe("metrics:all", "alerts:new", "system:events")

    try:
        await websocket.send_json({
            "event": "connected",
            "data": {
                "user_id": user_id,
                "role": payload.get("role"),
                "message": "Hospital Monitoring System — Real-time feed active",
                "developer": "MERO:TG@QP4RM",
            },
        })

        # Concurrent tasks: listen for Redis messages + handle client pings
        async def redis_listener() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json({
                            "event": message["channel"],
                            "data": data,
                        })
                    except Exception:
                        pass

        async def ping_handler() -> None:
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"event": "ping", "data": {}})
                except Exception:
                    break

        redis_task = asyncio.create_task(redis_listener())
        ping_task = asyncio.create_task(ping_handler())

        # Handle incoming client messages
        while True:
            try:
                msg = await websocket.receive_json()
                event = msg.get("event")

                if event == "subscribe_device":
                    device_id = msg.get("data", {}).get("device_id")
                    if device_id:
                        await pubsub.subscribe(f"metrics:device:{device_id}")
                        manager.join_room(f"device:{device_id}", user_id)
                        await websocket.send_json({
                            "event": "subscribed",
                            "data": {"device_id": device_id},
                        })

                elif event == "pong":
                    pass  # Heartbeat response

            except WebSocketDisconnect:
                break

    finally:
        redis_task.cancel()
        ping_task.cancel()
        await pubsub.unsubscribe()
        await pubsub.aclose()
        manager.disconnect(websocket, user_id)
