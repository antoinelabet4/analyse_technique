"""Vérifie le parsing contre des réponses réellement observées (capturées le
23/10/2026 par appel direct aux API publiques Binance et Kraken), pas des
échantillons inventés."""
from __future__ import annotations

import httpx
import pytest

from app.data import market
from app.data.market import fetch_binance_klines, fetch_kraken_ohlc

BINANCE_REPONSE_REELLE = [
    [
        1792540800000,
        "83028.14000000",
        "84898.00000000",
        "82635.32000000",
        "84093.42000000",
        "16544.48031000",
        1792627199999,
        "1388741748.82311660",
        3096152,
        "8138.40380000",
        "682753995.10599420",
        "0",
    ]
]

KRAKEN_REPONSE_REELLE = {
    "error": [],
    "result": {
        "XXBTZUSD": [
            [1730505600, "69490.1", "69858.8", "69060.0", "69300.0", "69444.7", "803.13883973", 19256]
        ],
        "last": 1730505600,
    },
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_binance_klines_parses_a_real_response(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(BINANCE_REPONSE_REELLE))
    candles = fetch_binance_klines("BTCUSDT", "1d")
    assert len(candles) == 1
    c = candles[0]
    assert c.time == "2026-10-21"
    assert c.open == 83028.14
    assert c.high == 84898.0
    assert c.low == 82635.32
    assert c.close == 84093.42


def test_fetch_kraken_ohlc_parses_a_real_response(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(KRAKEN_REPONSE_REELLE))
    candles = fetch_kraken_ohlc("XBTUSD", "1d")
    assert len(candles) == 1
    c = candles[0]
    assert c.open == 69490.1
    assert c.high == 69858.8
    assert c.low == 69060.0
    assert c.close == 69300.0


def test_fetch_binance_klines_raises_on_malformed_response(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({"not": "a list"}))
    with pytest.raises(market.SourceUnavailable):
        fetch_binance_klines("BTCUSDT", "1d")


def test_fetch_kraken_ohlc_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: _FakeResponse({"error": ["EQuery:Unknown asset pair"], "result": {}})
    )
    with pytest.raises(market.SourceUnavailable):
        fetch_kraken_ohlc("INVALID", "1d")
