import os
import re
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "POLY Multilingual Assistance Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "poly-agora-secret-key-change-in-production")
    
    # Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:////tmp/poly.db" if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else "sqlite:///./poly.db"
    )
    
    # Agora Configuration
    AGORA_APP_ID: str = os.getenv("AGORA_APP_ID", "")
    AGORA_APP_CERTIFICATE: str = os.getenv("AGORA_APP_CERTIFICATE", "")
    
    # AI Config
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_LIVE_MODEL: str = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.0-flash-live-001")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # CORS Allowed Origins
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    
    PORT: Any = 8000
    HOST: str = "0.0.0.0"

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, v):
        if isinstance(v, int):
            return v
        try:
            return int(str(v).strip())
        except Exception:
            numbers = re.findall(r"\b\d{2,5}\b", str(v))
            return int(numbers[-1]) if numbers else 8000

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore", env_file=".env")

settings = Settings()
