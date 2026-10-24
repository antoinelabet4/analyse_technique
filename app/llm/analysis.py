"""Orchestration du texte explicatif LLM : cache par bougie clôturée,
plafond quotidien, limitation de débit, contrôle automatique des
chiffres. Voir docs/specs-techniques/P1-texte-explicatif-llm.md.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from app.llm.facts_check import tous_les_nombres_sont_dans_facts

DEFAULT_CACHE_PATH = Path("/app/data/cache.db")
PLAFOND_QUOTIDIEN = 20
DEBIT_MINIMUM_SECONDES = 10

SECTIONS = ["tendance", "niveaux", "scenarios", "ce_qui_changerait", "risques"]

PROMPT_SYSTEME = """Tu rédiges un texte explicatif en français simple pour une application d'analyse technique crypto personnelle, à partir UNIQUEMENT du JSON "facts" fourni par l'utilisateur.

Règles strictes :
- N'utilise AUCUN chiffre qui n'est pas déjà présent dans le JSON fourni. N'invente, n'arrondis différemment et ne calcule aucune nouvelle valeur numérique.
- Aucune prédiction de prix, aucun ton péremptoire, aucun conseil d'achat ou de vente.
- Réponds uniquement en JSON valide avec exactement ces 5 clés, chaque valeur étant un paragraphe en français : "tendance", "niveaux", "scenarios", "ce_qui_changerait", "risques".
- Si une information manque dans le JSON fourni, dis-le explicitement dans le texte plutôt que de l'omettre silencieusement ou de la deviner."""


class PlafondAtteint(Exception):
    pass


class DebitDepasse(Exception):
    pass


class TexteNonFiable(Exception):
    """Levée quand le texte généré échoue deux fois au contrôle des chiffres."""


@dataclass
class ResultatAnalyseLLM:
    texte: dict
    source_cache: bool
    genere_le: str


def _connect(cache_path: Path) -> sqlite3.Connection:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cache_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses_llm (
            asset TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            derniere_bougie TEXT NOT NULL,
            texte_json TEXT NOT NULL,
            genere_le TEXT NOT NULL,
            PRIMARY KEY (asset, timeframe, derniere_bougie)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
            jour TEXT PRIMARY KEY,
            compte INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_dernier_appel (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            horodatage REAL NOT NULL
        )
        """
    )
    return conn


def _verifier_et_incrementer_plafond(conn: sqlite3.Connection, plafond: int | None = None) -> None:
    plafond = plafond if plafond is not None else PLAFOND_QUOTIDIEN
    jour = datetime.now(tz=timezone.utc).date().isoformat()
    row = conn.execute("SELECT compte FROM llm_usage WHERE jour = ?", (jour,)).fetchone()
    compte_actuel = row[0] if row else 0
    if compte_actuel >= plafond:
        raise PlafondAtteint(f"Plafond quotidien atteint ({plafond}/jour).")
    conn.execute(
        "INSERT INTO llm_usage (jour, compte) VALUES (?, 1) "
        "ON CONFLICT (jour) DO UPDATE SET compte = compte + 1",
        (jour,),
    )
    conn.commit()


def _verifier_debit(conn: sqlite3.Connection, minimum_secondes: int | None = None) -> None:
    minimum_secondes = minimum_secondes if minimum_secondes is not None else DEBIT_MINIMUM_SECONDES
    row = conn.execute("SELECT horodatage FROM llm_dernier_appel WHERE id = 1").fetchone()
    maintenant = datetime.now(tz=timezone.utc).timestamp()
    if row is not None and (maintenant - row[0]) < minimum_secondes:
        attente = minimum_secondes - (maintenant - row[0])
        raise DebitDepasse(f"Veuillez patienter {attente:.0f} secondes avant une nouvelle analyse.")
    conn.execute(
        "INSERT INTO llm_dernier_appel (id, horodatage) VALUES (1, ?) "
        "ON CONFLICT (id) DO UPDATE SET horodatage = excluded.horodatage",
        (maintenant,),
    )
    conn.commit()


def _lire_cache(conn: sqlite3.Connection, asset: str, timeframe: str, derniere_bougie: str) -> dict | None:
    row = conn.execute(
        "SELECT texte_json, genere_le FROM analyses_llm WHERE asset = ? AND timeframe = ? AND derniere_bougie = ?",
        (asset, timeframe, derniere_bougie),
    ).fetchone()
    if row is None:
        return None
    texte_json, genere_le = row
    return {"texte": json.loads(texte_json), "genere_le": genere_le}


def _ecrire_cache(conn: sqlite3.Connection, asset: str, timeframe: str, derniere_bougie: str, texte: dict) -> str:
    genere_le = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO analyses_llm (asset, timeframe, derniere_bougie, texte_json, genere_le)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (asset, timeframe, derniere_bougie) DO UPDATE SET
            texte_json = excluded.texte_json, genere_le = excluded.genere_le
        """,
        (asset, timeframe, derniere_bougie, json.dumps(texte), genere_le),
    )
    conn.commit()
    return genere_le


def _facts_pour_prompt(facts: dict) -> dict:
    """Retire les séries volumineuses (bougies, série du nuage) inutiles au
    texte qualitatif : réduit le coût par appel sans retirer aucune valeur
    résumée (prix, indicateurs, niveaux, scénarios...) dont dispose le LLM."""
    reduit = {k: v for k, v in facts.items() if k != "candles"}
    if isinstance(reduit.get("ichimoku"), dict):
        reduit["ichimoku"] = {k: v for k, v in reduit["ichimoku"].items() if k != "nuage_serie"}
    return reduit


def _appeler_llm(facts: dict, modele: str) -> dict:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=modele,
        max_tokens=1500,
        system=PROMPT_SYSTEME,
        messages=[{"role": "user", "content": json.dumps(_facts_pour_prompt(facts), ensure_ascii=False)}],
    )
    texte_brut = "".join(bloc.text for bloc in message.content if bloc.type == "text")
    texte = json.loads(texte_brut)
    for section in SECTIONS:
        if section not in texte:
            raise TexteNonFiable(f"Section manquante dans la réponse LLM : {section}")
    return texte


def generer_analyse(
    asset: str,
    timeframe: str,
    facts: dict,
    cache_path: Path = DEFAULT_CACHE_PATH,
    modele: str | None = None,
) -> ResultatAnalyseLLM:
    derniere_bougie = facts["candles"][-1]["time"]
    conn = _connect(cache_path)
    try:
        cache = _lire_cache(conn, asset, timeframe, derniere_bougie)
        if cache is not None:
            return ResultatAnalyseLLM(texte=cache["texte"], source_cache=True, genere_le=cache["genere_le"])

        _verifier_debit(conn)

        modele_utilise = modele or os.environ.get("LLM_MODEL", "claude-sonnet-5-5")

        # Le plafond compte chaque appel réel à l'API (une regénération en
        # consomme un deuxième), pas chaque clic utilisateur.
        _verifier_et_incrementer_plafond(conn)
        texte = _appeler_llm(facts, modele_utilise)
        conforme, manquants = tous_les_nombres_sont_dans_facts(json.dumps(texte, ensure_ascii=False), facts)
        if not conforme:
            _verifier_et_incrementer_plafond(conn)
            texte = _appeler_llm(facts, modele_utilise)
            conforme, manquants = tous_les_nombres_sont_dans_facts(json.dumps(texte, ensure_ascii=False), facts)
            if not conforme:
                raise TexteNonFiable(
                    f"Le texte généré contient des chiffres absents des données ({manquants}), non affiché."
                )

        genere_le = _ecrire_cache(conn, asset, timeframe, derniere_bougie, texte)
        return ResultatAnalyseLLM(texte=texte, source_cache=False, genere_le=genere_le)
    finally:
        conn.close()
