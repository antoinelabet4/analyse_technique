from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.market import ASSETS, SourceUnavailable
from app.engine.facts import build_facts
from app.fixtures import generate_demo_candles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Analyse technique crypto")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/test-candles")
def api_test_candles() -> list[dict]:
    return generate_demo_candles()


@app.get("/api/assets")
def api_assets() -> list[str]:
    return list(ASSETS.keys())


@app.get("/api/analysis/{asset}/{timeframe}")
def api_analysis(asset: str, timeframe: str) -> dict:
    asset = asset.upper()
    timeframe = timeframe.lower()
    if asset not in ASSETS:
        raise HTTPException(status_code=400, detail=f"Actif inconnu : {asset}")
    if timeframe not in ("1d", "1w"):
        raise HTTPException(status_code=400, detail=f"Timeframe inconnu : {timeframe}")
    try:
        return build_facts(asset, timeframe)
    except SourceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
