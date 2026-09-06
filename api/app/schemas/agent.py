from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class AgentInteractRequest(BaseModel):
    session_id: Optional[str] = None
    input_text: str
    language_override: Optional[str] = None

class AgentInteractResponse(BaseModel):
    session_id: str
    agora_channel: str
    turn_id: Optional[str] = None
    response_text: Optional[str] = None
    action: str
    state: Dict[str, Any]
    transcript: List[Dict[str, Any]]

class AgentSessionResponse(BaseModel):
    session_id: str
    agora_channel: str
    state: Dict[str, Any]
    transcript: List[Dict[str, Any]]
