import sys
import os
import traceback

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

app_err = None
try:
    from app.main import app
except Exception as e:
    app_err = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def error_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={"error": "Backend import failure", "traceback": app_err}
        )

__all__ = ["app"]
