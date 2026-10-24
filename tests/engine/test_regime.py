import pandas as pd

from app.engine.indicators import detect_structure, ichimoku, regime, sma
from tests.engine.conftest import candles_df


def test_regime_reports_price_above_moving_average():
    candles = candles_df(90)
    candles.loc[candles.index[-1], "close"] = float(candles["high"].max()) * 2
    mm = sma(candles["close"], 20)
    result = regime(candles, mm, ichimoku(candles))
    assert result.prix_vs_mm_longue == "au_dessus"


def test_regime_is_indisponible_before_enough_history_for_the_moving_average():
    candles = candles_df(10)
    mm = sma(candles["close"], 200)
    result = regime(candles, mm, ichimoku(candles))
    assert result.prix_vs_mm_longue == "indisponible"
    assert result.pente_mm_longue == "indisponible"


def test_detect_structure_is_indetermine_on_too_short_a_series():
    candles = pd.DataFrame({"high": [100, 101], "low": [99, 98], "close": [100, 99]})
    assert detect_structure(candles) == "indetermine"
