from fastapi import FastAPI
import sys
import os

app = FastAPI()

@app.get("/api/v1/health")
@app.get("/health")
def health():
    return {
        "status": "ok",
        "python_version": sys.version,
        "cwd": os.getcwd()
    }
