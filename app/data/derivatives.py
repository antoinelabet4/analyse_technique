"""Funding rate, open interest (Binance Futures) et contexte options
(Deribit). Voir docs/specs-techniques/P2-derives-macro.md.

Blocage géographique possible et non confirmé pour la France (vérifié
depuis une IP américaine lors de la rédaction de la spec) : chaque
fonction retourne `disponible=False` avec une raison explicite en cas
d'échec, jamais une valeur inventée.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from app.data import cache_utils

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
DERIBIT_BASE_URL = "https://www.deribit.com"
HTTP_TIMEOUT_SECONDS = 5.0
CACHE_TTL_SECONDES = 300
DEFAULT_CACHE_PATH = Path("/app/data/cache.db")

FUTURES_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "XRP": "XRPUSDT", "TAO": "TAOUSDT", "RENDER": "RENDERUSDT"}
OPTIONS_CURRENCIES = {"BTC", "ETH"}


@dataclass
class FundingOI:
    disponible: bool
    raison: str | None = None
    funding_rate: float | None = None
    open_interest: float | None = None


@dataclass
class OptionsContext:
    disponible: bool
    raison: str | None = None
    put_call_ratio_oi: float | None = None
    nb_instruments: int | None = None


def _fetch_funding_oi(asset: str) -> FundingOI:
    symbole = FUTURES_SYMBOLS.get(asset)
    if symbole is None:
        return FundingOI(disponible=False, raison=f"Pas de contrat futures connu pour {asset}")
    try:
        r1 = httpx.get(
            f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/premiumIndex",
            params={"symbol": symbole},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        r1.raise_for_status()
        funding = float(r1.json()["lastFundingRate"])
        r2 = httpx.get(
            f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/openInterest",
            params={"symbol": symbole},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        r2.raise_for_status()
        oi = float(r2.json()["openInterest"])
        return FundingOI(disponible=True, funding_rate=funding, open_interest=oi)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 451:
            return FundingOI(disponible=False, raison="Source bloquée depuis cette localisation (451)")
        return FundingOI(disponible=False, raison=f"Erreur HTTP {exc.response.status_code}")
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return FundingOI(disponible=False, raison=f"Erreur réseau ({type(exc).__name__})")


def get_funding_oi(asset: str, cache_path: Path = DEFAULT_CACHE_PATH) -> FundingOI:
    conn = cache_utils.connect(cache_path)
    try:
        cle = f"funding_oi:{asset}"
        cache = cache_utils.lire(conn, cle, CACHE_TTL_SECONDES)
        if cache is not None:
            return FundingOI(**cache)
        resultat = _fetch_funding_oi(asset)
        if resultat.disponible:
            cache_utils.ecrire(conn, cle, resultat.__dict__)
        return resultat
    finally:
        conn.close()


def _fetch_options_context(asset: str) -> OptionsContext:
    if asset not in OPTIONS_CURRENCIES:
        return OptionsContext(disponible=False, raison=f"Pas d'options Deribit suivies pour {asset}")
    try:
        r = httpx.get(
            f"{DERIBIT_BASE_URL}/api/v2/public/get_book_summary_by_currency",
            params={"currency": asset, "kind": "option"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        r.raise_for_status()
        resultats = r.json()["result"]
        calls_oi = sum(i["open_interest"] for i in resultats if i["instrument_name"].endswith("-C"))
        puts_oi = sum(i["open_interest"] for i in resultats if i["instrument_name"].endswith("-P"))
        ratio = (puts_oi / calls_oi) if calls_oi > 0 else None
        return OptionsContext(disponible=True, put_call_ratio_oi=ratio, nb_instruments=len(resultats))
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return OptionsContext(disponible=False, raison=str(exc))


def get_options_context(asset: str, cache_path: Path = DEFAULT_CACHE_PATH) -> OptionsContext:
    conn = cache_utils.connect(cache_path)
    try:
        cle = f"options:{asset}"
        cache = cache_utils.lire(conn, cle, CACHE_TTL_SECONDES)
        if cache is not None:
            return OptionsContext(**cache)
        resultat = _fetch_options_context(asset)
        if resultat.disponible:
            cache_utils.ecrire(conn, cle, resultat.__dict__)
        return resultat
    finally:
        conn.close()
