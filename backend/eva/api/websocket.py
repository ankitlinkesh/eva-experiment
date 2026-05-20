from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


websocket_router = APIRouter()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "status", "message": "Eva link online"})
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        return
