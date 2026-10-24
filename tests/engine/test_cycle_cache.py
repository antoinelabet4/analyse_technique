from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from app.data.market import Candle, CandlesResult, SourceUnavailable
from app.engine import cycle as cycle_module


def _candles_result(n: int = 200) -> CandlesResult:
    candles = [
        Candle(time=f"2020-W{i}", open=100.0, high=101.0, low=99.0, close=100.0 * math.exp(0.01 * i), volume=0.0)
        for i in range(n)
    ]
    return CandlesResult(candles=candles, source="binance", a_jour_le="2026-01-01T00:00:00+00:00", perime=False)


def test_get_btc_cycle_channel_calcule_et_met_en_cache(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    monkeypatch.setattr(cycle_module, "get_candles", lambda *a, **k: (appels.append(1), _candles_result())[1])

    r1 = cycle_module.get_btc_cycle_channel(cache_path=cache_path)
    r2 = cycle_module.get_btc_cycle_channel(cache_path=cache_path)

    assert r1.disponible is True
    assert r1.position == r2.position
    assert len(appels) == 1  # deuxième appel servi par le cache


def test_get_btc_cycle_channel_indisponible_si_source_echoue(tmp_path: Path, monkeypatch):
    def boom(*a, **k):
        raise SourceUnavailable("binance et kraken indisponibles")

    monkeypatch.setattr(cycle_module, "get_candles", boom)
    resultat = cycle_module.get_btc_cycle_channel(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False
    assert resultat.raison is not None
