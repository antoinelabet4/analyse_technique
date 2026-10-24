from __future__ import annotations

import httpx
import pytest

from app.notifications import telegram


class _FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erreur", request=None, response=self)


def test_envoyer_message_leve_si_variables_absentes(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(telegram.TelegramEnvoiEchec):
        telegram.envoyer_message("test")


def test_envoyer_message_appelle_l_api_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "faux-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    appels = []
    monkeypatch.setattr(httpx, "post", lambda url, **k: (appels.append((url, k)), _FakeResponse())[1])
    telegram.envoyer_message("bonjour")
    assert len(appels) == 1
    url, kwargs = appels[0]
    assert "faux-token" in url
    assert kwargs["json"]["chat_id"] == "12345"
    assert kwargs["json"]["text"] == "bonjour"


def test_envoyer_message_leve_si_telegram_echoue(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "faux-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(status_code=400))
    with pytest.raises(telegram.TelegramEnvoiEchec):
        telegram.envoyer_message("bonjour")
