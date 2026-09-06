from pydantic import BaseModel
from typing import Optional

class AgoraTokenRequest(BaseModel):
    channel_name: str
    uid: Optional[int] = 0
    role: Optional[int] = 1 # 1 = Publisher, 2 = Subscriber
    expire_seconds: Optional[int] = 86400

class AgoraTokenResponse(BaseModel):
    token: Optional[str]
    channel_name: str
    uid: int
    app_id: Optional[str]
    status: str
    message: str
