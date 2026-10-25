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
# Augmenté de 1500 à 4096 le 25/10/2026 : en production, les deux premiers
# appels réels (une fois la clé API configurée) ont échoué avec une
# réponse tronquée en plein milieu d'une chaîne, puis une réponse texte
# vide — cohérent avec un budget de tokens insuffisant si le modèle
# consomme des tokens de raisonnement avant le texte JSON visible.
MAX_TOKENS_REPONSE = 4096

SECTIONS = ["tendance", "niveaux", "scenarios", "ce_qui_changerait", "risques"]
# Demande explicite du propriétaire (25/10/2026), avec confirmation du
# format (badge dédié) et du disclaimer reformulé en conséquence : un
# verdict directionnel assumé, pas une simple description. Le contrôle
# anti-invention ne peut pas vérifier un jugement comme il vérifie un
# chiffre, c'est pourquoi le verdict est contraint à l'une de ces trois
# valeurs exactes plutôt que laissé en texte libre.
VERDICTS_VALIDES = {"acheter", "vendre", "attendre"}

PROMPT_SYSTEME = """Tu es un analyste technique crypto expérimenté qui rédige, en français simple, une analyse pour une application d'usage strictement personnel, à partir UNIQUEMENT du JSON "facts" fourni par l'utilisateur.

Règles strictes :
- N'utilise AUCUN chiffre qui n'est pas déjà présent dans le JSON fourni. N'invente, n'arrondis différemment et ne calcule aucune nouvelle valeur numérique.
- N'exprime jamais une variation en pourcentage, une différence, un ratio ou toute autre valeur calculée à partir des chiffres du JSON : seuls les chiffres qui y figurent déjà tels quels peuvent apparaître dans le texte.
- Tu peux mentionner une date si elle correspond à une date déjà présente dans le JSON (ex. "a_jour_le"), jamais une date ou une année inventée.
- Aucune prédiction de prix.
- Tranche avec un verdict explicite dans la clé "verdict" : exactement un seul mot parmi "acheter", "vendre" ou "attendre", rien d'autre. Base ce verdict uniquement sur ce qui est déjà dans le JSON (régime, niveaux les plus proches du prix actuel, RSI14, MACD, position dans le nuage Ichimoku) : jamais sur une intuition ou une information extérieure au JSON. Un prix proche d'un support avec un régime haussier et une dynamique qui s'améliore va plutôt vers "acheter" ; proche d'une résistance avec un régime baissier ou une dynamique qui se dégrade va plutôt vers "vendre" ; une situation mitigée ou un range sans signal net va vers "attendre".
- Réponds uniquement en JSON valide avec exactement ces 6 clés : "verdict", "tendance", "niveaux", "scenarios", "ce_qui_changerait", "risques". Les 5 dernières sont chacune un court paragraphe en français (3 phrases maximum, jamais une liste à puces).
- Sois synthétique, pas descriptif : ne récite pas chaque indicateur un par un dans l'ordre du JSON. Ne garde que ce qui compte pour lire la situation du moment, en priorisant toujours les niveaux (supports, résistances, nuage) les plus proches du prix actuel plutôt que les extrêmes du JSON, qui comptent moins pour une lecture à court terme.
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
    """Retire les séries volumineuses (bougies, série du nuage, des
    moyennes mobiles, du RSI, du MACD) inutiles au texte qualitatif :
    réduit le coût par appel sans retirer aucune valeur résumée (prix,
    indicateurs, niveaux, scénarios...) dont dispose le LLM."""
    reduit = {k: v for k, v in facts.items() if k not in ("candles", "moyennes_mobiles_serie", "rsi_serie")}
    if isinstance(reduit.get("ichimoku"), dict):
        reduit["ichimoku"] = {k: v for k, v in reduit["ichimoku"].items() if k != "nuage_serie"}
    if isinstance(reduit.get("macd"), dict):
        reduit["macd"] = {k: v for k, v in reduit["macd"].items() if k != "serie"}
    return reduit


def _appeler_llm(facts: dict, modele: str, chiffres_a_eviter: list[float] | None = None) -> dict:
    client = anthropic.Anthropic()
    system = PROMPT_SYSTEME
    if chiffres_a_eviter:
        # Réessai après un premier rejet : donner les chiffres fautifs au
        # modèle plutôt que de retenter à l'aveugle avec le même prompt
        # (bug du 25/10/2026 : sans ce retour, le deuxième essai répétait
        # souvent la même invention et échouait aussi).
        system += (
            "\n\nUne génération précédente a utilisé ces chiffres, absents du JSON fourni : "
            f"{chiffres_a_eviter}. Ne les réutilise sous aucun prétexte. Relis chaque chiffre "
            "avant de l'écrire et vérifie qu'il apparaît littéralement dans le JSON fourni."
        )
    message = client.messages.create(
        model=modele,
        max_tokens=MAX_TOKENS_REPONSE,
        system=system,
        messages=[{"role": "user", "content": json.dumps(_facts_pour_prompt(facts), ensure_ascii=False)}],
    )
    texte_brut = "".join(bloc.text for bloc in message.content if bloc.type == "text")
    try:
        texte = json.loads(texte_brut)
    except json.JSONDecodeError as exc:
        # Diagnostic explicite plutôt qu'une JSONDecodeError peu parlante
        # (bug du 25/10/2026 : la vraie cause — réponse tronquée ou vide —
        # était noyée dans une erreur de parsing sans contexte). On trace
        # la raison d'arrêt et la taille reçue, jamais le contenu intégral.
        raise TexteNonFiable(
            f"Réponse LLM non interprétable en JSON (stop_reason={message.stop_reason}, "
            f"{len(texte_brut)} caractère(s) reçu(s)) : {exc}"
        ) from exc
    for section in SECTIONS:
        if section not in texte:
            raise TexteNonFiable(f"Section manquante dans la réponse LLM : {section}")
    if texte.get("verdict") not in VERDICTS_VALIDES:
        raise TexteNonFiable(f"Verdict invalide dans la réponse LLM : {texte.get('verdict')!r}")
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
        try:
            texte = _appeler_llm(facts, modele_utilise)
        except TexteNonFiable:
            # Une réponse tronquée ou mal formée n'est pas forcément
            # reproductible (bug du 25/10/2026) : un seul réessai avant
            # d'abandonner, même logique que le contrôle des chiffres
            # ci-dessous. Si le deuxième essai échoue aussi, l'exception
            # remonte telle quelle.
            _verifier_et_incrementer_plafond(conn)
            texte = _appeler_llm(facts, modele_utilise)
        conforme, manquants = tous_les_nombres_sont_dans_facts(json.dumps(texte, ensure_ascii=False), facts)
        if not conforme:
            _verifier_et_incrementer_plafond(conn)
            texte = _appeler_llm(facts, modele_utilise, chiffres_a_eviter=manquants)
            conforme, manquants = tous_les_nombres_sont_dans_facts(json.dumps(texte, ensure_ascii=False), facts)
            if not conforme:
                raise TexteNonFiable(
                    f"Le texte généré contient des chiffres absents des données ({manquants}), non affiché."
                )

        genere_le = _ecrire_cache(conn, asset, timeframe, derniere_bougie, texte)
        return ResultatAnalyseLLM(texte=texte, source_cache=False, genere_le=genere_le)
    finally:
        conn.close()
