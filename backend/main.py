import sys
import os
import traceback

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app.main import app
except Exception:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def debug_err(path: str):
        return JSONResponse(
            status_code=500,
            content={"error": "FastAPI import failed", "traceback": err_tb}
        )

__all__ = ["app"]
