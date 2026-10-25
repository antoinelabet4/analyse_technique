import pandas as pd

from app.engine.indicators import ema, macd
from tests.engine.conftest import candles_df


def test_macd_ligne_matches_difference_of_emas():
    closes = candles_df(120)["close"]
    resultat = macd(closes)
    reference = ema(closes, 12) - ema(closes, 26)
    pd.testing.assert_series_equal(resultat.ligne, reference)


def test_macd_histogramme_matches_ligne_moins_signal():
    closes = candles_df(120)["close"]
    resultat = macd(closes)
    pd.testing.assert_series_equal(
        resultat.histogramme, resultat.ligne - resultat.signal, check_names=False
    )


def test_macd_est_nan_avant_assez_d_historique():
    closes = candles_df(10)["close"]
    resultat = macd(closes)
    assert resultat.ligne.isna().all()
    assert resultat.signal.isna().all()
