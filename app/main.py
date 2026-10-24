from __future__ import annotations

import hmac
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.market import ASSETS, SourceUnavailable
from app.engine.daily_summary import construire_resume_quotidien
from app.engine.facts import build_facts
from app.fixtures import generate_demo_candles
from app.llm.analysis import DebitDepasse, PlafondAtteint, TexteNonFiable, generer_analyse
from app.notifications.telegram import TelegramEnvoiEchec, envoyer_message

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Explicite plutôt que de dépendre du handler de secours par défaut de
# Python (silencieux dans certaines configurations de conteneur) : sans
# ça, une exception interceptée ne laissait aucune trace exploitable dans
# les logs Coolify, rendant le diagnostic impossible sans deviner.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

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
        # indisponible, etc.) : message explicite au client, jamais de
        # détail interne (trace, clé) exposé ; la trace complète part
        # dans les logs serveur pour pouvoir diagnostiquer sans deviner.
        logger.exception("Échec de l'appel LLM pour %s/%s", asset, timeframe)
        raise HTTPException(status_code=502, detail="Le texte explicatif est indisponible pour le moment.") from exc
    return {
        "texte": resultat.texte,
        "source_cache": resultat.source_cache,
        "genere_le": resultat.genere_le,
    }


@app.post("/api/daily-trigger")
def api_daily_trigger(x_trigger_token: str | None = Header(default=None)) -> dict:
    token_attendu = os.environ.get("N8N_TRIGGER_TOKEN")
    if not token_attendu or not x_trigger_token or not hmac.compare_digest(x_trigger_token, token_attendu):
        raise HTTPException(status_code=401, detail="Token de déclenchement invalide ou absent")
    try:
        resume = construire_resume_quotidien()
        envoyer_message(resume)
    except TelegramEnvoiEchec as exc:
        raise HTTPException(status_code=502, detail="Échec de l'envoi Telegram") from exc
    return {"statut": "envoye"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.json")
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.json")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    # Servi depuis la racine (pas /static/) pour que sa portée par défaut
    # couvre toute l'app ("/"), condition requise pour l'installabilité
    # PWA (Chrome/Android notamment).
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
