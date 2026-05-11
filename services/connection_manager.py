"""
Observer Pattern: manages WebSocket connections per game (PIN) and broadcasts events.
All participants (host + players) for a PIN are "observers"; when state changes,
the ConnectionManager notifies all by sending the same message (broadcast).
"""

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:

    def __init__(self) -> None:
        self._connections: dict[str, dict[str, WebSocket]] = {}

    def connect(
        self,
        websocket: WebSocket,
        pin: str,
        client_id: str,
    ) -> None:
        if pin not in self._connections:
            self._connections[pin] = {}
        self._connections[pin][client_id] = websocket
    
    def disconnect(self, pin: str, client_id: str) -> None:
        if pin in self._connections:
            self._connections[pin].pop(client_id, None)
            if not self._connections[pin]:
                del self._connections[pin]

    async def broadcast(self, pin: str, message: dict[str, Any] | str) -> None:
        if pin not in self._connections:
            return
        payload = json.dumps(message) if isinstance(message, dict) else message
        dead: list[str] = []
        for cid, ws in self._connections[pin].items():
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self._connections[pin].pop(cid, None)
        if pin in self._connections and not self._connections[pin]:
            del self._connections[pin]

    def connection_count(self, pin: str) -> int:
        return len(self._connections.get(pin, {}))
