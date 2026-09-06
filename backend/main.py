import sys
import os

# Ensure the backend directory is on the Python path so that
# 'from app.xxx import ...' works correctly in Vercel serverless environment
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app  # noqa: F401 - Vercel looks for 'app' at module level

__all__ = ["app"]
