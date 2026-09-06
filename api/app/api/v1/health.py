from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "agora_configured": bool(settings.AGORA_APP_ID),
        "database_configured": bool(settings.DATABASE_URL)
    }
