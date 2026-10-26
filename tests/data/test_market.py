from __future__ import annotations

from pathlib import Path

import pytest

from app.data import market
from app.data.market import Candle, SourceUnavailable, get_candles


def _bougies_factices(n: int = 3) -> list[Candle]:
    return [
        Candle(time=f"2026-01-0{i + 1}", open=100.0, high=101.0, low=99.0, close=100.5, volume=10.0)
        for i in range(n)
    ]


def test_get_candles_utilise_binance_quand_disponible(tmp_path: Path, monkeypatch):
    bougies = _bougies_factices()
    monkeypatch.setattr(market, "fetch_binance_klines", lambda *a, **k: bougies)
    monkeypatch.setattr(
        market,
        "fetch_kraken_ohlc",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Kraken ne doit pas être appelé")),
    )

    result = get_candles("BTC", "1d", cache_path=tmp_path / "cache.db")

    assert result.source == "binance"
    assert result.perime is False
    assert result.candles == bougies


def test_get_candles_bascule_sur_kraken_si_binance_echoue(tmp_path: Path, monkeypatch):
    bougies = _bougies_factices()
    monkeypatch.setattr(
        market,
        "fetch_binance_klines",
        lambda *a, **k: (_ for _ in ()).throw(SourceUnavailable("binance down")),
    )
    monkeypatch.setattr(market, "fetch_kraken_ohlc", lambda *a, **k: bougies)

    result = get_candles("BTC", "1d", cache_path=tmp_path / "cache.db")

    assert result.source == "kraken"
    assert result.perime is False
    assert result.candles == bougies


def test_get_candles_sert_le_cache_perime_si_les_deux_sources_echouent(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    bougies = _bougies_factices()

    # Premier appel : Binance répond, remplit le cache.
    monkeypatch.setattr(market, "fetch_binance_klines", lambda *a, **k: bougies)
    monkeypatch.setattr(
        market,
        "fetch_kraken_ohlc",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("non appelé au 1er tour")),
    )
    get_candles("BTC", "1d", cache_path=cache_path)

    # Deuxième appel : les deux sources échouent, le cache doit servir.
    monkeypatch.setattr(
        market,
        "fetch_binance_klines",
        lambda *a, **k: (_ for _ in ()).throw(SourceUnavailable("binance down")),
    )
    monkeypatch.setattr(
        market,
        "fetch_kraken_ohlc",
        lambda *a, **k: (_ for _ in ()).throw(SourceUnavailable("kraken down")),
    )

    result = get_candles("BTC", "1d", cache_path=cache_path)

    assert result.source == "cache"
    assert result.perime is True
    assert result.candles == bougies


def test_get_candles_leve_une_erreur_si_aucune_source_ni_cache(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        market,
        "fetch_binance_klines",
        lambda *a, **k: (_ for _ in ()).throw(SourceUnavailable("binance down")),
    )
    monkeypatch.setattr(
        market,
        "fetch_kraken_ohlc",
        lambda *a, **k: (_ for _ in ()).throw(SourceUnavailable("kraken down")),
    )

    with pytest.raises(SourceUnavailable):
        get_candles("BTC", "1d", cache_path=tmp_path / "cache.db")


def test_get_candles_rejette_un_actif_inconnu(tmp_path: Path):
    with pytest.raises(ValueError):
        get_candles("INCONNU", "1d", cache_path=tmp_path / "cache.db")


def test_get_candles_rejette_un_timeframe_inconnu(tmp_path: Path):
    with pytest.raises(ValueError):
        get_candles("BTC", "1h", cache_path=tmp_path / "cache.db")
