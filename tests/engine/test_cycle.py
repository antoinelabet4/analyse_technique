import math

import numpy as np
import pandas as pd
import pytest

from app.engine.cycle import regression_log_lineaire


def _candles_croissance_exponentielle(n: int = 200, taux: float = 0.01) -> pd.DataFrame:
    prix = [100.0 * math.exp(taux * i) for i in range(n)]
    return pd.DataFrame({"close": prix})


def test_regression_suit_une_croissance_exponentielle_parfaite():
    candles = _candles_croissance_exponentielle()
    canal = regression_log_lineaire(candles)
    # Sans bruit, le prix actuel doit être très proche de la tendance.
    assert canal.tendance_actuelle == pytest.approx(candles["close"].iloc[-1], rel=0.01)
    assert canal.position == "dans"
    assert canal.borne_basse_actuelle < canal.tendance_actuelle < canal.borne_haute_actuelle


def test_position_au_dessus_du_canal():
    candles = _candles_croissance_exponentielle()
    candles.loc[candles.index[-1], "close"] *= 3  # pic bien au-dessus du bruit habituel
    canal = regression_log_lineaire(candles)
    assert canal.position == "au_dessus"


def test_position_en_dessous_du_canal():
    candles = _candles_croissance_exponentielle()
    candles.loc[candles.index[-1], "close"] /= 3
    canal = regression_log_lineaire(candles)
    assert canal.position == "en_dessous"


def test_erreur_si_historique_insuffisant():
    with pytest.raises(ValueError):
        regression_log_lineaire(pd.DataFrame({"close": [100.0]}))
