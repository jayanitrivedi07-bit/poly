from fastapi import APIRouter, HTTPException
from app.schemas.agora import AgoraTokenRequest, AgoraTokenResponse
from app.core.agora import generate_agora_rtc_token

router = APIRouter()

@router.post("/rtc-token", response_model=AgoraTokenResponse)
def get_agora_rtc_token(request: AgoraTokenRequest):
    """
    Generates a dynamic Agora WebRTC token for real-time voice channel communication.
    """
    result = generate_agora_rtc_token(
        channel_name=request.channel_name,
        uid=request.uid or 0,
        role=request.role or 1,
        expire_seconds=request.expire_seconds or 86400
    )
    return result
