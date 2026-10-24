"""Envoi d'un message via l'API Telegram Bot. Jeton et chat_id lus
uniquement depuis l'environnement, jamais en dur. Voir
docs/specs-techniques/P3-onchain-cycle-n8n.md.
"""
from __future__ import annotations

import os

import httpx

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
HTTP_TIMEOUT_SECONDS = 10.0


class TelegramEnvoiEchec(Exception):
    pass


def envoyer_message(texte: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise TelegramEnvoiEchec("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID absent de l'environnement")
    try:
        reponse = httpx.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": texte, "parse_mode": "HTML"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        reponse.raise_for_status()
    except httpx.HTTPError as exc:
        raise TelegramEnvoiEchec(str(exc)) from exc
