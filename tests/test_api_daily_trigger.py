from fastapi.testclient import TestClient

import app.main as main_module
from app.notifications.telegram import TelegramEnvoiEchec

client = TestClient(main_module.app)


def test_daily_trigger_401_sans_token(monkeypatch):
    monkeypatch.setenv("N8N_TRIGGER_TOKEN", "secret-correct")
    resp = client.post("/api/daily-trigger")
    assert resp.status_code == 401


def test_daily_trigger_401_avec_mauvais_token(monkeypatch):
    monkeypatch.setenv("N8N_TRIGGER_TOKEN", "secret-correct")
    resp = client.post("/api/daily-trigger", headers={"X-Trigger-Token": "mauvais"})
    assert resp.status_code == 401


def test_daily_trigger_200_avec_bon_token(monkeypatch):
    monkeypatch.setenv("N8N_TRIGGER_TOKEN", "secret-correct")
    monkeypatch.setattr(main_module, "construire_resume_quotidien", lambda: "résumé test")
    appels = []
    monkeypatch.setattr(main_module, "envoyer_message", lambda texte: appels.append(texte))
    resp = client.post("/api/daily-trigger", headers={"X-Trigger-Token": "secret-correct"})
    assert resp.status_code == 200
    assert resp.json() == {"statut": "envoye"}
    assert appels == ["résumé test"]


def test_daily_trigger_502_si_telegram_echoue(monkeypatch):
    monkeypatch.setenv("N8N_TRIGGER_TOKEN", "secret-correct")
    monkeypatch.setattr(main_module, "construire_resume_quotidien", lambda: "résumé test")

    def boom(texte):
        raise TelegramEnvoiEchec("échec")

    monkeypatch.setattr(main_module, "envoyer_message", boom)
    resp = client.post("/api/daily-trigger", headers={"X-Trigger-Token": "secret-correct"})
    assert resp.status_code == 502


def test_daily_trigger_401_si_pas_de_token_configure_sur_le_serveur(monkeypatch):
    monkeypatch.delenv("N8N_TRIGGER_TOKEN", raising=False)
    resp = client.post("/api/daily-trigger", headers={"X-Trigger-Token": "peu-importe"})
    assert resp.status_code == 401
