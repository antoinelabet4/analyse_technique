from __future__ import annotations

import pandas as pd

from app.fixtures import generate_demo_candles


def candles_df(days: int = 90) -> pd.DataFrame:
    """Jeu de bougies figé (même génération que la page de démo du P0),
    réutilisé ici comme donnée de test reproductible pour le moteur."""
    return pd.DataFrame(generate_demo_candles(days=days))
