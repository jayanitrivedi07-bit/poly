from fastapi import APIRouter
from app.api.v1 import health, agora, agent, cases, auth, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Agent Authentication"])
api_router.include_router(agora.router, prefix="/agora", tags=["Agora RTC"])
api_router.include_router(agent.router, prefix="/agent", tags=["Poly Voice Agent"])
api_router.include_router(cases.router, prefix="/cases", tags=["Case Management"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSockets"])
