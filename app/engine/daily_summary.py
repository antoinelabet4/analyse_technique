"""Assemble le résumé quotidien envoyé par Telegram (déclenché par le
n8n du propriétaire). Construit exclusivement à partir des "facts" déjà
calculés par le moteur déterministe, jamais de nouveau chiffre inventé
ici. Voir docs/specs-techniques/P3-onchain-cycle-n8n.md.
"""
from __future__ import annotations

from app.data.market import ASSETS
from app.engine.facts import build_facts


def _ligne_btc(facts: dict) -> list[str]:
    lignes = [
        f"<b>BTC</b> : {facts['prix_actuel']}",
        f"Régime : prix {facts['regime']['prix_vs_mm_longue']} de la MM longue (pente {facts['regime']['pente_mm_longue']}), structure {facts['regime']['structure']}",
    ]
    onchain = facts.get("onchain")
    if onchain and onchain.get("disponible"):
        lignes.append(
            f"On-chain ({onchain['date_donnee']}) : SOPR {onchain['sopr']} · MVRV {onchain['mvrv']} "
            f"(Z {onchain['mvrv_zscore']}) · Puell {onchain['puell_multiple']}"
        )
    else:
        lignes.append("On-chain : indisponible aujourd'hui")

    cycle = facts.get("cycle")
    if cycle and cycle.get("disponible"):
        lignes.append(
            f"Canal de cycle (régression log, statistique, pas une prédiction) : prix {cycle['position']} "
            f"du canal [{cycle['borne_basse_actuelle']:.0f} – {cycle['borne_haute_actuelle']:.0f}]"
        )
    else:
        lignes.append("Canal de cycle : indisponible aujourd'hui")

    for s in facts["scenarios"]:
        if s["cible"] is not None:
            lignes.append(f"Scénario {s['type']} : {s['condition_cloture']} · cible {s['cible']}")
    return lignes


def _ligne_alt(asset: str, facts: dict) -> str:
    fr = facts.get("force_relative_btc")
    tendance = fr["tendance"] if fr else "n.d."
    return f"{asset} : {facts['prix_actuel']} (force relative vs BTC : {tendance})"


def construire_resume_quotidien() -> str:
    lignes = ["<b>Analyse technique quotidienne</b> (automatisée, pas un conseil financier)", ""]

    btc_facts = build_facts("BTC", "1d")
    lignes.extend(_ligne_btc(btc_facts))
    lignes.append("")

    for asset in ASSETS:
        if asset == "BTC":
            continue
        try:
            facts = build_facts(asset, "1d")
            lignes.append(_ligne_alt(asset, facts))
        except Exception:
            lignes.append(f"{asset} : indisponible aujourd'hui")

    return "\n".join(lignes)
