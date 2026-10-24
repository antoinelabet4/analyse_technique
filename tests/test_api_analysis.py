import pytest
from fastapi.testclient import TestClient

from app.data.derivatives import FundingOI, OptionsContext
from app.data.macro import Dominance, FearGreed, IndiceMacro
from app.data.market import Candle, CandlesResult, SourceUnavailable
from app.data.onchain import OnchainMetrics
from app.engine import facts as facts_module
from app.engine.cycle import CanalCycle
from app.fixtures import generate_demo_candles
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _pas_de_reseau_derives_macro(monkeypatch):
    """Ces sources ont leur propre suite de tests (tests/data/test_derivatives.py,
    tests/data/test_macro.py, tests/data/test_onchain.py, tests/engine/test_cycle*.py) ;
    ici on les neutralise pour ne jamais dépendre du réseau réel dans les
    tests de l'endpoint /api/analysis."""
    monkeypatch.setattr(facts_module, "get_funding_oi", lambda asset: FundingOI(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_options_context", lambda asset: OptionsContext(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_fear_greed", lambda: FearGreed(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_btc_dominance", lambda: Dominance(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_sp500", lambda: IndiceMacro(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_dxy", lambda: IndiceMacro(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(facts_module, "get_onchain_metrics", lambda: OnchainMetrics(disponible=False, raison="non testé ici"))
    monkeypatch.setattr(
        facts_module,
        "get_btc_cycle_channel",
        lambda: CanalCycle(tendance_actuelle=0, borne_haute_actuelle=0, borne_basse_actuelle=0, position="indisponible", nb_bougies=0, disponible=False, raison="non testé ici"),
    )


def _candles_result(days: int = 90) -> CandlesResult:
    raw = generate_demo_candles(days=days)
    candles = [
        Candle(time=c["time"], open=c["open"], high=c["high"], low=c["low"], close=c["close"], volume=0.0)
        for c in raw
    ]
    return CandlesResult(candles=candles, source="binance", a_jour_le="2026-01-01T00:00:00+00:00", perime=False)


def test_api_analysis_btc_1d_has_no_force_relative(monkeypatch):
    monkeypatch.setattr(facts_module, "get_candles", lambda asset, timeframe, limit=300: _candles_result())
    resp = client.get("/api/analysis/BTC/1d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["actif"] == "BTC"
    assert data["force_relative_btc"] is None
    assert "ichimoku" in data and "niveaux" in data and "scenarios" in data
    assert len(data["ichimoku"]["nuage_serie"]) > 0
    point = data["ichimoku"]["nuage_serie"][0]
    assert set(point.keys()) == {"time", "senkou_a", "senkou_b"}
    assert data["derives"]["funding_oi"]["disponible"] is False
    assert data["macro"]["fear_greed"]["disponible"] is False
    # Les moyennes mobiles sont fournies en courbe complète (pas seulement
    # la valeur actuelle) pour être tracées comme une vraie ligne sur le
    # graphique, pas juste un niveau fixe.
    assert set(data["moyennes_mobiles_serie"].keys()) == {"mm50", "mm200"}
    assert len(data["moyennes_mobiles_serie"]["mm50"]) > 0
    point = data["moyennes_mobiles_serie"]["mm50"][0]
    assert set(point.keys()) == {"time", "valeur"}


def test_api_analysis_alt_includes_force_relative(monkeypatch):
    monkeypatch.setattr(facts_module, "get_candles", lambda asset, timeframe, limit=300: _candles_result())
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
    def boom(asset, timeframe, limit=300):
        raise SourceUnavailable("down")

    monkeypatch.setattr(facts_module, "get_candles", boom)
    resp = client.get("/api/analysis/BTC/1d")
    assert resp.status_code == 503


def test_api_assets_lists_the_five_assets():
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    assert set(resp.json()) == {"BTC", "ETH", "XRP", "TAO", "RENDER"}
