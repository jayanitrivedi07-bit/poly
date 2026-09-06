import sys
import os
import traceback

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

task_backend = os.path.abspath("/var/task/backend")
if os.path.exists(task_backend) and task_backend not in sys.path:
    sys.path.insert(0, task_backend)

try:
    from app.main import app
except Exception as e:
    err_msg = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_route(full_path: str):
        return JSONResponse(
            status_code=500,
            content={"error": "FastAPI failed to initialize", "detail": err_msg}
        )

from mangum import Mangum
handler = Mangum(app, lifespan="off")

__all__ = ["app", "handler"]
