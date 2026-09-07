import sys
import os
import traceback

# Ensure backend directory is discoverable in Python's module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Also ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from backend.app.main import app  # type: ignore
except Exception:
    try:
        from app.main import app  # type: ignore
    except Exception as e:
        err_tb = traceback.format_exc()
        try:
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse

            app = FastAPI()

            @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
            async def debug_err(path: str):
                return JSONResponse(
                    status_code=500,
                    content={"error": "FastAPI initialization failed in api/index.py", "traceback": err_tb}
                )
        except Exception:
            raise e

__all__ = ["app"]

