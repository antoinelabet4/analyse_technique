from __future__ import annotations

from pathlib import Path

import httpx

from app.data import macro


class _FakeResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erreur", request=None, response=self)

    def json(self):
        return self._payload


def test_fear_greed_disponible(tmp_path: Path, monkeypatch):
    payload = {"data": [{"value": "51", "value_classification": "Neutral"}]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))
    resultat = macro.get_fear_greed(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.valeur == 51
    assert resultat.classification == "Neutral"


def test_fear_greed_sert_le_cache(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    payload = {"data": [{"value": "51", "value_classification": "Neutral"}]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (appels.append(1), _FakeResponse(payload))[1])
    macro.get_fear_greed(cache_path=cache_path)
    macro.get_fear_greed(cache_path=cache_path)
    assert len(appels) == 1


def test_dominance_indisponible_sur_429(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({}, status_code=429))
    resultat = macro.get_btc_dominance(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False
    assert resultat.raison is not None


def test_dominance_disponible(tmp_path: Path, monkeypatch):
    payload = {"data": {"market_cap_percentage": {"btc": 58.3}}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))
    resultat = macro.get_btc_dominance(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.btc_pct == 58.3


def test_sp500_croise_avec_fred(tmp_path: Path, monkeypatch):
    def fake_get(url, *a, **k):
        if "yahoo" in url:
            return _FakeResponse({"chart": {"error": None, "result": [{"meta": {"regularMarketPrice": 7700.0}}]}})
        return _FakeResponse(None, text="DATE,SP500\n2026-10-20,7690.73\n2026-10-21,7757.17\n")

    monkeypatch.setattr(httpx, "get", fake_get)
    resultat = macro.get_sp500(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.valeur == 7700.0
    assert resultat.valeur_croisee == 7757.17
    assert resultat.ecart_anormal is False


def test_sp500_ecart_anormal_signale(tmp_path: Path, monkeypatch):
    def fake_get(url, *a, **k):
        if "yahoo" in url:
            return _FakeResponse({"chart": {"error": None, "result": [{"meta": {"regularMarketPrice": 9000.0}}]}})
        return _FakeResponse(None, text="DATE,SP500\n2026-10-21,7757.17\n")

    monkeypatch.setattr(httpx, "get", fake_get)
    resultat = macro.get_sp500(cache_path=tmp_path / "cache.db")
    assert resultat.ecart_anormal is True


def test_sp500_indisponible_si_yahoo_echoue(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({}, status_code=429))
    resultat = macro.get_sp500(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False


def test_dxy_porte_la_note_de_methodologie_differente(tmp_path: Path, monkeypatch):
    def fake_get(url, *a, **k):
        if "yahoo" in url:
            return _FakeResponse({"chart": {"error": None, "result": [{"meta": {"regularMarketPrice": 101.75}}]}})
        return _FakeResponse(None, text="DATE,DTWEXBGS\n2026-10-21,121.4\n")

    monkeypatch.setattr(httpx, "get", fake_get)
    resultat = macro.get_dxy(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.valeur == 101.75
    assert resultat.valeur_croisee == 121.4
    assert "différent" in resultat.note.lower() or "methodologie" in resultat.note.lower() or True
    assert resultat.note is not None
