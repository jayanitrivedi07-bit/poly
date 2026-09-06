import sys
import os

# Ensure the api directory is in sys.path so 'from app.xxx import ...' resolves directly
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.main import app

__all__ = ["app"]
