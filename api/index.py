from fastapi import FastAPI
import sys
import os

app = FastAPI()

@app.get("/api/v1/health")
def health():
    items = {}
    for p in ["/var/task", ".", ".."]:
        try:
            items[p] = os.listdir(p)
        except Exception as e:
            items[p] = str(e)
    return {
        "status": "ok",
        "python": sys.version,
        "dirs": items
    }
