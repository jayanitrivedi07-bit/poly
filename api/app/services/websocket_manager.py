import json
import logging
import asyncio
from typing import Dict, List, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Maps session_id -> Set[WebSocket]
        self._session_connections: Dict[str, Set[WebSocket]] = {}
        # Connections subscribed to global queue/dashboard events
        self._dashboard_connections: Set[WebSocket] = set()

    async def connect_session(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self._session_connections:
            self._session_connections[session_id] = set()
        self._session_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected to session {session_id}")

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self._dashboard_connections.add(websocket)
        logger.info("WebSocket connected to dashboard global queue")

    def disconnect_session(self, session_id: str, websocket: WebSocket):
        if session_id in self._session_connections:
            self._session_connections[session_id].discard(websocket)
            if not self._session_connections[session_id]:
                del self._session_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")

    def disconnect_dashboard(self, websocket: WebSocket):
        self._dashboard_connections.discard(websocket)
        logger.info("WebSocket disconnected from dashboard")

    async def broadcast_session_event(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcasts a typed event envelope to all WebSocket clients on a session."""
        envelope = {
            "event": event_type,
            "session_id": session_id,
            "data": data
        }
        connections = self._session_connections.get(session_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(envelope)
            except Exception as e:
                logger.warning(f"Failed to send session WS event: {e}")
                self.disconnect_session(session_id, ws)

    async def broadcast_dashboard_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcasts a typed event envelope to all dashboard subscribers."""
        envelope = {
            "event": event_type,
            "data": data
        }
        connections = self._dashboard_connections.copy()
        for ws in connections:
            try:
                await ws.send_json(envelope)
            except Exception as e:
                logger.warning(f"Failed to send dashboard WS event: {e}")
                self.disconnect_dashboard(ws)

websocket_manager = WebSocketManager()
