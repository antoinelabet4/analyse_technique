from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.fixtures import generate_demo_candles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Analyse technique crypto")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/test-candles")
def api_test_candles() -> list[dict]:
    return generate_demo_candles()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
