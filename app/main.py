from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.market import ASSETS, SourceUnavailable
from app.engine.facts import build_facts
from app.fixtures import generate_demo_candles
from app.llm.analysis import DebitDepasse, PlafondAtteint, TexteNonFiable, generer_analyse

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


@app.post("/api/analysis-llm/{asset}/{timeframe}")
def api_analysis_llm(asset: str, timeframe: str) -> dict:
    asset = asset.upper()
    timeframe = timeframe.lower()
    if asset not in ASSETS:
        raise HTTPException(status_code=400, detail=f"Actif inconnu : {asset}")
    if timeframe not in ("1d", "1w"):
        raise HTTPException(status_code=400, detail=f"Timeframe inconnu : {timeframe}")
    try:
        facts = build_facts(asset, timeframe)
    except SourceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        resultat = generer_analyse(asset, timeframe, facts)
    except PlafondAtteint as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except DebitDepasse as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except TexteNonFiable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        # Erreur non anticipée côté LLM (clé manquante/invalide, Anthropic
        # indisponible, etc.) : message explicite, jamais de détail
        # interne (trace, clé) renvoyé au client.
        raise HTTPException(status_code=502, detail="Le texte explicatif est indisponible pour le moment.") from exc
    return {
        "texte": resultat.texte,
        "source_cache": resultat.source_cache,
        "genere_le": resultat.genere_le,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
