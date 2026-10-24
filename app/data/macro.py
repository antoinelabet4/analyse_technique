"""Contexte macro : Fear & Greed, dominance BTC, DXY et S&P 500 (ces deux
derniers croisés avec une seconde source officielle quand possible).
Voir docs/specs-techniques/P2-derives-macro.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from app.data import cache_utils

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/"
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_USER_AGENT = "Mozilla/5.0"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
HTTP_TIMEOUT_SECONDS = 5.0
CACHE_TTL_SECONDES = 900
DEFAULT_CACHE_PATH = Path("/app/data/cache.db")
ECART_ANORMAL_SP500_PCT = 2.0

DXY_NOTE = (
    "FRED DTWEXBGS n'est pas l'indice ICE DXY : panier de devises et "
    "méthodologie différents, affiché à titre de contexte complémentaire "
    "uniquement, pas comme un croisement du même chiffre."
)


@dataclass
class FearGreed:
    disponible: bool
    raison: str | None = None
    valeur: int | None = None
    classification: str | None = None


@dataclass
class Dominance:
    disponible: bool
    raison: str | None = None
    btc_pct: float | None = None


@dataclass
class IndiceMacro:
    disponible: bool
    raison: str | None = None
    valeur: float | None = None
    valeur_croisee: float | None = None
    source_croisee: str | None = None
    ecart_anormal: bool = False
    note: str | None = None


def _avec_cache(conn, cle: str, fetch):
    cache = cache_utils.lire(conn, cle, CACHE_TTL_SECONDES)
    if cache is not None:
        return cache
    resultat = fetch()
    if resultat.get("disponible"):
        cache_utils.ecrire(conn, cle, resultat)
    return resultat


def _fetch_fear_greed() -> dict:
    try:
        r = httpx.get(ALTERNATIVE_ME_URL, params={"limit": 1}, timeout=HTTP_TIMEOUT_SECONDS)
        r.raise_for_status()
        item = r.json()["data"][0]
        return {"disponible": True, "raison": None, "valeur": int(item["value"]), "classification": item["value_classification"]}
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        return {"disponible": False, "raison": str(exc), "valeur": None, "classification": None}


def get_fear_greed(cache_path: Path = DEFAULT_CACHE_PATH) -> FearGreed:
    conn = cache_utils.connect(cache_path)
    try:
        return FearGreed(**_avec_cache(conn, "fear_greed", _fetch_fear_greed))
    finally:
        conn.close()


def _fetch_dominance() -> dict:
    try:
        r = httpx.get(COINGECKO_GLOBAL_URL, timeout=HTTP_TIMEOUT_SECONDS)
        r.raise_for_status()
        pct = r.json()["data"]["market_cap_percentage"]["btc"]
        return {"disponible": True, "raison": None, "btc_pct": float(pct)}
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return {"disponible": False, "raison": str(exc), "btc_pct": None}


def get_btc_dominance(cache_path: Path = DEFAULT_CACHE_PATH) -> Dominance:
    conn = cache_utils.connect(cache_path)
    try:
        return Dominance(**_avec_cache(conn, "dominance_btc", _fetch_dominance))
    finally:
        conn.close()


def _yahoo_prix(symbole: str) -> float:
    r = httpx.get(
        YAHOO_CHART_URL.format(symbol=symbole),
        headers={"User-Agent": YAHOO_USER_AGENT},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    data = r.json()
    if data["chart"].get("error"):
        raise ValueError(str(data["chart"]["error"]))
    return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])


def _fred_dernier(series_id: str) -> float:
    r = httpx.get(FRED_CSV_URL, params={"id": series_id}, timeout=HTTP_TIMEOUT_SECONDS)
    r.raise_for_status()
    lignes = [l for l in r.text.strip().splitlines()[1:] if "," in l]
    for ligne in reversed(lignes):
        _date, valeur = ligne.rsplit(",", 1)
        if valeur not in (".", ""):
            return float(valeur)
    raise ValueError("Aucune valeur FRED exploitable")


def _fetch_sp500() -> dict:
    try:
        prix = _yahoo_prix("%5EGSPC")
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        return {
            "disponible": False, "raison": f"Yahoo Finance indisponible : {exc}",
            "valeur": None, "valeur_croisee": None, "source_croisee": None, "ecart_anormal": False, "note": None,
        }
    croise = None
    ecart_anormal = False
    try:
        croise = _fred_dernier("SP500")
        ecart_anormal = abs(prix - croise) / croise * 100 > ECART_ANORMAL_SP500_PCT
    except (httpx.HTTPError, ValueError):
        croise = None
    return {
        "disponible": True, "raison": None, "valeur": prix,
        "valeur_croisee": croise, "source_croisee": "FRED (SP500)" if croise is not None else None,
        "ecart_anormal": ecart_anormal, "note": None,
    }


def get_sp500(cache_path: Path = DEFAULT_CACHE_PATH) -> IndiceMacro:
    conn = cache_utils.connect(cache_path)
    try:
        return IndiceMacro(**_avec_cache(conn, "sp500", _fetch_sp500))
    finally:
        conn.close()


def _fetch_dxy() -> dict:
    try:
        prix = _yahoo_prix("DX-Y.NYB")
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        return {
            "disponible": False, "raison": f"Yahoo Finance indisponible : {exc}",
            "valeur": None, "valeur_croisee": None, "source_croisee": None, "ecart_anormal": False, "note": None,
        }
    contexte = None
    try:
        contexte = _fred_dernier("DTWEXBGS")
    except (httpx.HTTPError, ValueError):
        contexte = None
    return {
        "disponible": True, "raison": None, "valeur": prix,
        "valeur_croisee": contexte,
        "source_croisee": "FRED DTWEXBGS (indicateur différent)" if contexte is not None else None,
        "ecart_anormal": False, "note": DXY_NOTE,
    }


def get_dxy(cache_path: Path = DEFAULT_CACHE_PATH) -> IndiceMacro:
    conn = cache_utils.connect(cache_path)
    try:
        return IndiceMacro(**_avec_cache(conn, "dxy", _fetch_dxy))
    finally:
        conn.close()
