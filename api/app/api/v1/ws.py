import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    await websocket_manager.connect_session(session_id, websocket)
    try:
        while True:
            # Keep connection open for incoming messages / ping frames
            data = await websocket.receive_text()
            logger.debug(f"WS message from session {session_id}: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect_session(session_id, websocket)
    except Exception as e:
        logger.warning(f"Error in session WS {session_id}: {e}")
        websocket_manager.disconnect_session(session_id, websocket)

@router.websocket("/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    await websocket_manager.connect_dashboard(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WS message from dashboard: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect_dashboard(websocket)
    except Exception as e:
        logger.warning(f"Error in dashboard WS: {e}")
        websocket_manager.disconnect_dashboard(websocket)
