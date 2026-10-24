"""Force relative d'un alt vs BTC, telle que décrite dans le brief d'origine
("Force relative vs BTC + contexte BTC"). Fonction pure, aucun I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RelativeStrength:
    ratio_actuel: float
    tendance: str  # "hausse" | "baisse" | "plat" | "indisponible"
    variation_pct_periode: float | None


def relative_strength(closes_actif: pd.Series, closes_btc: pd.Series, periode: int = 30) -> RelativeStrength:
    """`closes_actif` et `closes_btc` doivent être alignées sur les mêmes dates
    (même longueur, même ordre chronologique) ; aligner en amont si besoin."""
    if len(closes_actif) != len(closes_btc) or len(closes_actif) == 0:
        return RelativeStrength(ratio_actuel=float("nan"), tendance="indisponible", variation_pct_periode=None)

    ratio = closes_actif / closes_btc
    ratio_actuel = float(ratio.iloc[-1])

    if len(ratio) <= periode:
        return RelativeStrength(ratio_actuel=ratio_actuel, tendance="indisponible", variation_pct_periode=None)

    ratio_debut_periode = float(ratio.iloc[-1 - periode])
    variation_pct = (ratio_actuel - ratio_debut_periode) / ratio_debut_periode * 100

    if variation_pct > 1:
        tendance = "hausse"
    elif variation_pct < -1:
        tendance = "baisse"
    else:
        tendance = "plat"

    return RelativeStrength(ratio_actuel=ratio_actuel, tendance=tendance, variation_pct_periode=variation_pct)
