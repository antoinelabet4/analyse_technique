from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.data import derivatives


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erreur", request=None, response=self)

    def json(self):
        return self._payload


def test_funding_oi_disponible_sur_succes(tmp_path: Path, monkeypatch):
    reponses = iter([
        _FakeResponse({"lastFundingRate": "0.0001"}),
        _FakeResponse({"openInterest": "12345.6"}),
    ])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(reponses))
    resultat = derivatives.get_funding_oi("BTC", cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.funding_rate == 0.0001
    assert resultat.open_interest == 12345.6


def test_funding_oi_indisponible_sur_451(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({"code": 0}, status_code=451))
    resultat = derivatives.get_funding_oi("BTC", cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False
    assert resultat.raison is not None


def test_funding_oi_actif_sans_contrat_futures(tmp_path: Path):
    resultat = derivatives.get_funding_oi("DOGE", cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False


def test_funding_oi_sert_le_cache_sans_rappeler_le_reseau(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []

    def fake_get(*a, **k):
        appels.append(1)
        if len(appels) == 1:
            return _FakeResponse({"lastFundingRate": "0.0002"})
        return _FakeResponse({"openInterest": "999"})

    monkeypatch.setattr(httpx, "get", fake_get)
    derivatives.get_funding_oi("BTC", cache_path=cache_path)
    derivatives.get_funding_oi("BTC", cache_path=cache_path)
    assert len(appels) == 2  # un seul cycle funding+OI, pas deux


def test_options_context_calcule_le_ratio_put_call(tmp_path: Path, monkeypatch):
    payload = {
        "result": [
            {"instrument_name": "BTC-1-C", "open_interest": 10.0},
            {"instrument_name": "BTC-1-P", "open_interest": 5.0},
        ]
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))
    resultat = derivatives.get_options_context("BTC", cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.put_call_ratio_oi == 0.5
    assert resultat.nb_instruments == 2


def test_options_context_indisponible_pour_actif_non_suivi(tmp_path: Path):
    resultat = derivatives.get_options_context("XRP", cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False
