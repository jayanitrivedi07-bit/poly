from fastapi import FastAPI
import sys
import os
import traceback

app = FastAPI()

@app.get("/api/v1/health")
def health():
    results = {}
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    modules_to_test = [
        "app.core.config",
        "app.core.agora",
        "app.database.session",
        "app.models.all_models",
        "app.schemas.agent",
        "app.services.session_manager",
        "app.agents.poly_agent",
        "app.api.v1.health",
        "app.api.v1.agent",
        "app.api.router",
        "app.main",
    ]
    for mod in modules_to_test:
        try:
            __import__(mod)
            results[mod] = "OK"
        except Exception:
            results[mod] = traceback.format_exc()
            break
            
    return results

__all__ = ["app"]
