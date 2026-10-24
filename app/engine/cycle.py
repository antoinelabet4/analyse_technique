"""Canal de régression log-linéaire sur l'historique des prix BTC, comme
repère de cycle. Donnée statistique dérivée, jamais une prédiction de
prix. Voir docs/specs-techniques/P3-onchain-cycle-n8n.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.data import cache_utils
from app.data.market import SourceUnavailable, get_candles

CACHE_TTL_SECONDES = 6 * 3600
DEFAULT_CACHE_PATH = Path("/app/data/cache.db")
HISTORIQUE_LIMIT = 1000


@dataclass
class CanalCycle:
    tendance_actuelle: float
    borne_haute_actuelle: float
    borne_basse_actuelle: float
    position: str  # "au_dessus" | "dans" | "en_dessous"
    nb_bougies: int
    disponible: bool = True
    raison: str | None = None


def regression_log_lineaire(candles: pd.DataFrame) -> CanalCycle:
    closes = candles["close"].astype(float)
    n = len(closes)
    if n < 2:
        raise ValueError("Historique insuffisant pour une régression de cycle")

    t = np.arange(n)
    log_prix = np.log(closes.to_numpy())
    pente, ordonnee = np.polyfit(t, log_prix, 1)

    tendance_log = ordonnee + pente * t
    residus = log_prix - tendance_log
    ecart_type = float(np.std(residus))

    tendance_actuelle = float(np.exp(tendance_log[-1]))
    borne_haute = float(np.exp(tendance_log[-1] + ecart_type))
    borne_basse = float(np.exp(tendance_log[-1] - ecart_type))

    prix_actuel = float(closes.iloc[-1])
    if prix_actuel > borne_haute:
        position = "au_dessus"
    elif prix_actuel < borne_basse:
        position = "en_dessous"
    else:
        position = "dans"

    return CanalCycle(
        tendance_actuelle=tendance_actuelle,
        borne_haute_actuelle=borne_haute,
        borne_basse_actuelle=borne_basse,
        position=position,
        nb_bougies=n,
    )


def get_btc_cycle_channel(cache_path: Path = DEFAULT_CACHE_PATH) -> CanalCycle:
    """Calcule (et met en cache 6h) le canal de cycle BTC sur l'historique
    hebdomadaire le plus long disponible (limité à l'historique Binance,
    pas l'historique complet de Bitcoin depuis 2009 — voir la spec)."""
    conn = cache_utils.connect(cache_path)
    try:
        cache = cache_utils.lire(conn, "cycle_btc", CACHE_TTL_SECONDES)
        if cache is not None:
            return CanalCycle(**cache)
        try:
            resultat_marche = get_candles("BTC", "1w", limit=HISTORIQUE_LIMIT)
            candles = pd.DataFrame([c.__dict__ for c in resultat_marche.candles])
            canal = regression_log_lineaire(candles)
        except (SourceUnavailable, ValueError) as exc:
            return CanalCycle(
                tendance_actuelle=0, borne_haute_actuelle=0, borne_basse_actuelle=0,
                position="indisponible", nb_bougies=0, disponible=False, raison=str(exc),
            )
        cache_utils.ecrire(conn, "cycle_btc", asdict(canal))
        return canal
    finally:
        conn.close()
