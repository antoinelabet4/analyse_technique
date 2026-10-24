from __future__ import annotations

from pathlib import Path

import httpx

from app.data import onchain


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erreur", request=None, response=self)

    def json(self):
        return self._payload


def test_onchain_metrics_disponible(tmp_path: Path, monkeypatch):
    def fake_get(url, *a, **k):
        if url.endswith("/sopr"):
            return _FakeResponse([{"d": "2026-10-17", "sopr": 1.0016}])
        if url.endswith("/mvrv"):
            return _FakeResponse([{"d": "2026-10-17", "mvrv": 1.5232}])
        if url.endswith("/mvrv-zscore"):
            return _FakeResponse([{"d": "2026-10-17", "mvrvZscore": 0.9178}])
        if url.endswith("/puell-multiple"):
            return _FakeResponse([{"d": "2026-10-17", "puellMultiple": 0.9942}])
        raise AssertionError(f"URL inattendue : {url}")

    monkeypatch.setattr(httpx, "get", fake_get)
    resultat = onchain.get_onchain_metrics(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is True
    assert resultat.sopr == 1.0016
    assert resultat.mvrv == 1.5232
    assert resultat.mvrv_zscore == 0.9178
    assert resultat.puell_multiple == 0.9942
    assert resultat.date_donnee == "2026-10-17"


def test_onchain_metrics_indisponible_si_source_echoue(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({}, status_code=503))
    resultat = onchain.get_onchain_metrics(cache_path=tmp_path / "cache.db")
    assert resultat.disponible is False
    assert resultat.raison is not None


def test_onchain_metrics_sert_le_cache(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []

    def fake_get(url, *a, **k):
        appels.append(url)
        if url.endswith("/sopr"):
            return _FakeResponse([{"d": "2026-10-17", "sopr": 1.0}])
        if url.endswith("/mvrv"):
            return _FakeResponse([{"d": "2026-10-17", "mvrv": 1.0}])
        if url.endswith("/mvrv-zscore"):
            return _FakeResponse([{"d": "2026-10-17", "mvrvZscore": 1.0}])
        return _FakeResponse([{"d": "2026-10-17", "puellMultiple": 1.0}])

    monkeypatch.setattr(httpx, "get", fake_get)
    onchain.get_onchain_metrics(cache_path=cache_path)
    onchain.get_onchain_metrics(cache_path=cache_path)
    assert len(appels) == 4  # un seul cycle de 4 appels, pas huit
