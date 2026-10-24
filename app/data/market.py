"""Récupération des chandeliers de marché : Binance en priorité, Kraken en
secours, cache SQLite comme filet de sécurité si les deux échouent.

Voir docs/specs-techniques/P1-recuperation-donnees.md.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

BINANCE_BASE_URL = "https://data-api.binance.vision"
KRAKEN_BASE_URL = "https://api.kraken.com"
HTTP_TIMEOUT_SECONDS = 5.0
DEFAULT_CACHE_PATH = Path("/app/data/cache.db")

ASSETS: dict[str, dict[str, str]] = {
    "BTC": {"binance": "BTCUSDT", "kraken": "XBTUSD"},
    "ETH": {"binance": "ETHUSDT", "kraken": "ETHUSD"},
    "XRP": {"binance": "XRPUSDT", "kraken": "XRPUSD"},
    "TAO": {"binance": "TAOUSDT", "kraken": "TAOUSD"},
    "RENDER": {"binance": "RENDERUSDT", "kraken": "RENDERUSD"},
}

BINANCE_INTERVALS = {"1d": "1d", "1w": "1w"}
KRAKEN_INTERVAL_MINUTES = {"1d": 1440, "1w": 10080}


class SourceUnavailable(Exception):
    """Levée quand une source de données ne peut pas être interrogée ou
    renvoie une réponse inexploitable. Jamais remplacée par une donnée
    inventée : voir get_candles pour le repli sur le cache."""


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class CandlesResult:
    candles: list[Candle]
    source: str  # "binance" | "kraken" | "cache"
    a_jour_le: str  # ISO datetime UTC
    perime: bool = False


# --------------------------------------------------------------------------
# Sources live
# --------------------------------------------------------------------------


def fetch_binance_klines(symbol: str, interval: str, limit: int = 300) -> list[Candle]:
    try:
        reponse = httpx.get(
            f"{BINANCE_BASE_URL}/api/v3/klines",
            params={"symbol": symbol, "interval": BINANCE_INTERVALS[interval], "limit": limit},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        reponse.raise_for_status()
        donnees_brutes = reponse.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SourceUnavailable(f"Binance indisponible pour {symbol} : {exc}") from exc

    try:
        return [
            Candle(
                time=datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc).date().isoformat(),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
            for item in donnees_brutes
        ]
    except (IndexError, TypeError, ValueError) as exc:
        raise SourceUnavailable(f"Réponse Binance mal formée pour {symbol} : {exc}") from exc


def fetch_kraken_ohlc(pair: str, interval: str, limit: int = 300) -> list[Candle]:
    try:
        reponse = httpx.get(
            f"{KRAKEN_BASE_URL}/0/public/OHLC",
            params={"pair": pair, "interval": KRAKEN_INTERVAL_MINUTES[interval]},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        reponse.raise_for_status()
        charge_utile = reponse.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SourceUnavailable(f"Kraken indisponible pour {pair} : {exc}") from exc

    if charge_utile.get("error"):
        raise SourceUnavailable(f"Kraken a renvoyé une erreur pour {pair} : {charge_utile['error']}")

    try:
        cle_resultat = next(k for k in charge_utile["result"] if k != "last")
        donnees_brutes = charge_utile["result"][cle_resultat]
        bougies = [
            Candle(
                time=datetime.fromtimestamp(item[0], tz=timezone.utc).date().isoformat(),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[6]),
            )
            for item in donnees_brutes
        ]
    except (StopIteration, IndexError, TypeError, ValueError, KeyError) as exc:
        raise SourceUnavailable(f"Réponse Kraken mal formée pour {pair} : {exc}") from exc

    return bougies[-limit:]


# --------------------------------------------------------------------------
# Cache SQLite (filet de sécurité uniquement)
# --------------------------------------------------------------------------


def _connect(cache_path: Path) -> sqlite3.Connection:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candles_cache (
            asset TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            candles_json TEXT NOT NULL,
            PRIMARY KEY (asset, timeframe)
        )
        """
    )
    return conn


def _write_cache(conn: sqlite3.Connection, asset: str, timeframe: str, source: str, candles: list[Candle]) -> None:
    conn.execute(
        """
        INSERT INTO candles_cache (asset, timeframe, source, fetched_at, candles_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (asset, timeframe) DO UPDATE SET
            source = excluded.source,
            fetched_at = excluded.fetched_at,
            candles_json = excluded.candles_json
        """,
        (
            asset,
            timeframe,
            source,
            datetime.now(tz=timezone.utc).isoformat(),
            json.dumps([asdict(c) for c in candles]),
        ),
    )
    conn.commit()


def _read_cache(conn: sqlite3.Connection, asset: str, timeframe: str) -> CandlesResult | None:
    row = conn.execute(
        "SELECT source, fetched_at, candles_json FROM candles_cache WHERE asset = ? AND timeframe = ?",
        (asset, timeframe),
    ).fetchone()
    if row is None:
        return None
    source, fetched_at, candles_json = row
    candles = [Candle(**c) for c in json.loads(candles_json)]
    return CandlesResult(candles=candles, source="cache", a_jour_le=fetched_at, perime=True)


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------


def get_candles(asset: str, timeframe: str, cache_path: Path = DEFAULT_CACHE_PATH, limit: int = 300) -> CandlesResult:
    if asset not in ASSETS:
        raise ValueError(f"Actif inconnu : {asset}")
    if timeframe not in BINANCE_INTERVALS:
        raise ValueError(f"Timeframe inconnu : {timeframe}")

    symboles = ASSETS[asset]
    conn = _connect(cache_path)
    try:
        for source_name, fetch in (
            ("binance", lambda: fetch_binance_klines(symboles["binance"], timeframe, limit)),
            ("kraken", lambda: fetch_kraken_ohlc(symboles["kraken"], timeframe, limit)),
        ):
            try:
                candles = fetch()
            except SourceUnavailable:
                continue
            _write_cache(conn, asset, timeframe, source_name, candles)
            return CandlesResult(
                candles=candles,
                source=source_name,
                a_jour_le=datetime.now(tz=timezone.utc).isoformat(),
                perime=False,
            )

        cache = _read_cache(conn, asset, timeframe)
        if cache is not None:
            return cache

        raise SourceUnavailable(
            f"Binance et Kraken indisponibles pour {asset}/{timeframe}, aucun cache disponible."
        )
    finally:
        conn.close()
