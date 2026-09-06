from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent: dict

class AgentProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_online: bool
