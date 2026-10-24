"""Métriques on-chain BTC (SOPR, MVRV, MVRV Z-score, Puell Multiple).
Source communautaire non officielle (bitcoin-data.com) : pas de garantie
de pérennité, délai d'environ une semaine, jamais présenté comme temps
réel. Voir docs/specs-techniques/P3-onchain-cycle-n8n.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from app.data import cache_utils

BASE_URL = "https://bitcoin-data.com/v1"
HTTP_TIMEOUT_SECONDS = 5.0
CACHE_TTL_SECONDES = 6 * 3600
DEFAULT_CACHE_PATH = Path("/app/data/cache.db")


@dataclass
class OnchainMetrics:
    disponible: bool
    raison: str | None = None
    date_donnee: str | None = None
    sopr: float | None = None
    mvrv: float | None = None
    mvrv_zscore: float | None = None
    puell_multiple: float | None = None


def _fetch_metrique(endpoint: str, champ: str) -> tuple[str, float]:
    r = httpx.get(f"{BASE_URL}/{endpoint}", timeout=HTTP_TIMEOUT_SECONDS)
    r.raise_for_status()
    donnees = r.json()
    if not donnees:
        raise ValueError(f"Réponse vide pour {endpoint}")
    dernier = donnees[-1]
    return dernier["d"], float(dernier[champ])


def _fetch_onchain_metrics() -> OnchainMetrics:
    try:
        date_sopr, sopr = _fetch_metrique("sopr", "sopr")
        _date_mvrv, mvrv = _fetch_metrique("mvrv", "mvrv")
        _date_z, mvrv_z = _fetch_metrique("mvrv-zscore", "mvrvZscore")
        _date_puell, puell = _fetch_metrique("puell-multiple", "puellMultiple")
        return OnchainMetrics(
            disponible=True,
            date_donnee=date_sopr,
            sopr=sopr,
            mvrv=mvrv,
            mvrv_zscore=mvrv_z,
            puell_multiple=puell,
        )
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        return OnchainMetrics(disponible=False, raison=f"Erreur source on-chain ({type(exc).__name__})")


def get_onchain_metrics(cache_path: Path = DEFAULT_CACHE_PATH) -> OnchainMetrics:
    conn = cache_utils.connect(cache_path)
    try:
        cache = cache_utils.lire(conn, "onchain_btc", CACHE_TTL_SECONDES)
        if cache is not None:
            return OnchainMetrics(**cache)
        resultat = _fetch_onchain_metrics()
        if resultat.disponible:
            cache_utils.ecrire(conn, "onchain_btc", resultat.__dict__)
        return resultat
    finally:
        conn.close()
