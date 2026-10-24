from fastapi.testclient import TestClient

from app.data.market import Candle, CandlesResult, SourceUnavailable
from app.engine import facts as facts_module
from app.fixtures import generate_demo_candles
from app.main import app

client = TestClient(app)


def _candles_result(days: int = 90) -> CandlesResult:
    raw = generate_demo_candles(days=days)
    candles = [
        Candle(time=c["time"], open=c["open"], high=c["high"], low=c["low"], close=c["close"], volume=0.0)
        for c in raw
    ]
    return CandlesResult(candles=candles, source="binance", a_jour_le="2026-01-01T00:00:00+00:00", perime=False)


def test_api_analysis_btc_1d_has_no_force_relative(monkeypatch):
    monkeypatch.setattr(facts_module, "get_candles", lambda asset, timeframe: _candles_result())
    resp = client.get("/api/analysis/BTC/1d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["actif"] == "BTC"
    assert data["force_relative_btc"] is None
    assert "ichimoku" in data and "niveaux" in data and "scenarios" in data


def test_api_analysis_alt_includes_force_relative(monkeypatch):
    monkeypatch.setattr(facts_module, "get_candles", lambda asset, timeframe: _candles_result())
    resp = client.get("/api/analysis/ETH/1d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["actif"] == "ETH"
    assert data["force_relative_btc"] is not None
    assert "tendance" in data["force_relative_btc"]


def test_api_analysis_rejects_unknown_asset():
    resp = client.get("/api/analysis/DOGE/1d")
    assert resp.status_code == 400


def test_api_analysis_rejects_unknown_timeframe():
    resp = client.get("/api/analysis/BTC/1h")
    assert resp.status_code == 400


def test_api_analysis_returns_503_when_source_unavailable(monkeypatch):
    def boom(asset, timeframe):
        raise SourceUnavailable("down")

    monkeypatch.setattr(facts_module, "get_candles", boom)
    resp = client.get("/api/analysis/BTC/1d")
    assert resp.status_code == 503


def test_api_assets_lists_the_five_assets():
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    assert set(resp.json()) == {"BTC", "ETH", "XRP", "TAO", "RENDER"}
