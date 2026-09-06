from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.schemas.agent import AgentInteractRequest, AgentInteractResponse, AgentSessionResponse
from app.services.session_manager import session_manager

router = APIRouter()

@router.post("/session", response_model=AgentSessionResponse)
def get_or_create_agent_session(session_id: str = None):
    """
    Initializes or retrieves an active Poly voice session.
    """
    session = session_manager.get_or_create(session_id)
    return {
        "session_id": session.session_id,
        "agora_channel": session.agora_channel,
        "state": session.state,
        "transcript": session.transcript
    }

@router.post("/interact", response_model=AgentInteractResponse)
def interact_with_agent(request: AgentInteractRequest):
    """
    Processes a caller turn through PolyAgent (Language detection, Safety check, Gemini LLM reasoning, Confidence evaluator).
    """
    session = session_manager.get_or_create(request.session_id)
    result = session.interact(request.input_text)
    return result

@router.post("/escalate", response_model=AgentSessionResponse)
def trigger_agent_escalation(session_id: str, reason: str = "Explicit caller request"):
    """
    Manually triggers human escalation for a session.
    """
    session = session_manager.get_or_create(session_id)
    session.state["escalation_required"] = True
    session.state["escalation_reason"] = reason
    session._persist_escalated_case()
    return {
        "session_id": session.session_id,
        "agora_channel": session.agora_channel,
        "state": session.state,
        "transcript": session.transcript
    }

@router.websocket("/ws/{session_id}")
async def agent_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time WebSocket connection streaming agent state updates and turns.
    """
    await websocket.accept()
    session = session_manager.get_or_create(session_id)
    
    # Send initial state
    await websocket.send_json({
        "event": "session_init",
        "state": session.state,
        "transcript": session.transcript
    })

    try:
        while True:
            data = await websocket.receive_json()
            if "input_text" in data:
                result = session.interact(data["input_text"])
                await websocket.send_json({
                    "event": "turn_complete",
                    "result": result
                })
    except WebSocketDisconnect:
        pass
