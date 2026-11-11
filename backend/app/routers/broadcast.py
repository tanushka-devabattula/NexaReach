"""Broadcast router.
Provides a simple WebSocket endpoint for real‑time public announcements.
Clients connect to /broadcast/ws and receive JSON messages with optional
language filtering.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.security import require_role
from typing import List, Dict

router = APIRouter(prefix="/broadcast", tags=["Broadcast"])

# In‑memory connections store – sufficient for demo/mock implementation
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.language_map: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, language: str | None = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.language_map[websocket] = (language or "en").lower()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.language_map.pop(websocket, None)

    async def broadcast(self, message: dict, language: str | None = None):
        target_lang = (language or "en").lower()
        for connection in list(self.active_connections):
            conn_lang = self.language_map.get(connection, "en")
            if conn_lang == target_lang:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, language: str | None = None):
    await manager.connect(websocket, language)
    try:
        while True:
            # Keep connection alive – we don't expect inbound messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Helper endpoint for the server (or admin UI) to push a broadcast
@router.post(
    "/send",
    summary="Send a public announcement to connected clients",
    dependencies=[Depends(require_role("admin", "campaign_manager"))],
)
def send_announcement(message: str, language: str | None = None):
    # In a real app this would be async; here we fire‑and‑forget using background task
    import threading
    def _send():
        import asyncio
        asyncio.run(manager.broadcast({"message": message, "language": language or "en"}, language))
    threading.Thread(target=_send, daemon=True).start()
    return {"detail": "Announcement queued"}
