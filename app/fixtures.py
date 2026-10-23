"""Données de démonstration pour la page de test du P0.

Jeu de chandeliers entièrement figé, jamais présenté comme une donnée de
marché réelle : la page affiche un bandeau explicite à ce sujet.
"""
from __future__ import annotations

from datetime import date, timedelta


def generate_demo_candles(days: int = 90) -> list[dict]:
    """Génère une série de chandeliers déterministe (même sortie à chaque appel).

    Marche aléatoire simple à graine fixe, uniquement pour avoir une forme
    de courbe réaliste à afficher ; ce n'est pas une simulation de marché.
    """
    seed = 42
    price = 50000.0
    start = date(2026, 1, 1)
    candles = []
    for i in range(days):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        delta_pct = ((seed % 2000) - 1000) / 10000  # -10% .. +10% du pas
        open_ = price
        close = max(1.0, open_ * (1 + delta_pct))
        high = max(open_, close) * 1.01
        low = min(open_, close) * 0.99
        candles.append(
            {
                "time": (start + timedelta(days=i)).isoformat(),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
            }
        )
        price = close
    return candles
