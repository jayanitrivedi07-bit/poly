from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from app.schemas.auth import LoginRequest, TokenResponse, AgentProfileResponse
from app.database.session import SessionLocal
from app.models.all_models import Agent
from app.core.security import verify_password, hash_password, create_access_token, decode_access_token

router = APIRouter()

def ensure_seed_agent(db):
    """Ensures default support specialist agent exists for demo testing."""
    agent = db.query(Agent).filter(Agent.email == "priya.sharma@poly.support").first()
    if not agent:
        agent = Agent(
            full_name="Priya Sharma",
            email="priya.sharma@poly.support",
            hashed_password=hash_password("poly2026"),
            role="Support Specialist",
            is_online=True
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    return agent

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """Authenticates Support Specialist agent and returns JWT token."""
    db = SessionLocal()
    try:
        ensure_seed_agent(db)
        agent = db.query(Agent).filter(Agent.email == request.email).first()
        if not agent or not verify_password(request.password, agent.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"sub": agent.id, "email": agent.email, "role": agent.role})
        return {
            "access_token": token,
            "token_type": "bearer",
            "agent": {
                "id": agent.id,
                "full_name": agent.full_name,
                "email": agent.email,
                "role": agent.role,
                "is_online": agent.is_online
            }
        }
    finally:
        db.close()

@router.get("/me", response_model=AgentProfileResponse)
def get_current_agent(authorization: Optional[str] = Header(None)):
    """Retrieves authenticated agent profile from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == payload.get("sub")).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {
            "id": agent.id,
            "full_name": agent.full_name,
            "email": agent.email,
            "role": agent.role,
            "is_online": agent.is_online
        }
    finally:
        db.close()
