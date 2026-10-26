from fastapi.testclient import TestClient

import app.main as main_module
from app.llm.analysis import DebitDepasse, PlafondAtteint, ResultatAnalyseLLM, TexteNonFiable

client = TestClient(main_module.app)

FACTS_FACTICES = {"candles": [{"time": "2026-01-01"}], "actif": "BTC"}


def test_api_analysis_llm_retourne_le_texte(monkeypatch):
    monkeypatch.setattr(main_module, "build_facts", lambda asset, timeframe: FACTS_FACTICES)
    monkeypatch.setattr(
        main_module,
        "generer_analyse",
        lambda asset, timeframe, facts: ResultatAnalyseLLM(
            texte={"tendance": "ok"}, source_cache=False, genere_le="2026-01-01T00:00:00+00:00"
        ),
    )
    resp = client.post("/api/analysis-llm/BTC/1d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["texte"] == {"tendance": "ok"}
    assert data["source_cache"] is False


def test_api_analysis_llm_rejette_actif_inconnu():
    resp = client.post("/api/analysis-llm/INCONNU/1d")
    assert resp.status_code == 400


def test_api_analysis_llm_429_si_plafond_atteint(monkeypatch):
    monkeypatch.setattr(main_module, "build_facts", lambda asset, timeframe: FACTS_FACTICES)

    def boom(asset, timeframe, facts):
        raise PlafondAtteint("Plafond quotidien atteint (20/jour).")

    monkeypatch.setattr(main_module, "generer_analyse", boom)
    resp = client.post("/api/analysis-llm/BTC/1d")
    assert resp.status_code == 429


def test_api_analysis_llm_429_si_debit_depasse(monkeypatch):
    monkeypatch.setattr(main_module, "build_facts", lambda asset, timeframe: FACTS_FACTICES)

    def boom(asset, timeframe, facts):
        raise DebitDepasse("Veuillez patienter.")

    monkeypatch.setattr(main_module, "generer_analyse", boom)
    resp = client.post("/api/analysis-llm/BTC/1d")
    assert resp.status_code == 429


def test_api_analysis_llm_502_si_texte_non_fiable(monkeypatch):
    monkeypatch.setattr(main_module, "build_facts", lambda asset, timeframe: FACTS_FACTICES)

    def boom(asset, timeframe, facts):
        raise TexteNonFiable("chiffre invente")

    monkeypatch.setattr(main_module, "generer_analyse", boom)
    resp = client.post("/api/analysis-llm/BTC/1d")
    assert resp.status_code == 502


def test_api_analysis_llm_502_sur_erreur_inattendue_sans_fuite_de_details(monkeypatch, caplog):
    monkeypatch.setattr(main_module, "build_facts", lambda asset, timeframe: FACTS_FACTICES)

    def boom(asset, timeframe, facts):
        raise TypeError("Could not resolve authentication method, api_key=sk-secret-xyz")

    monkeypatch.setattr(main_module, "generer_analyse", boom)
    with caplog.at_level("ERROR", logger="app"):
        resp = client.post("/api/analysis-llm/BTC/1d")
    assert resp.status_code == 502
    assert "sk-secret-xyz" not in resp.text
    # La trace complète doit, elle, être exploitable côté serveur : c'est
    # le seul moyen de diagnostiquer une vraie panne (clé invalide,
    # Anthropic indisponible...) sans deviner (bug trouvé le 24/10/2026 :
    # l'exception était avalée sans aucune trace dans les logs).
    assert "Could not resolve authentication method" in caplog.text
