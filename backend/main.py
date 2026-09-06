import sys
import os
import traceback

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app.main import app  # noqa: F401
except Exception as exc:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={"error": "FastAPI initialization failed", "traceback": err_tb}
        )

__all__ = ["app"]
