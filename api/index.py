import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

task_backend = "/var/task/backend"
if os.path.exists(task_backend) and task_backend not in sys.path:
    sys.path.insert(0, task_backend)

from app.main import app

__all__ = ["app"]
