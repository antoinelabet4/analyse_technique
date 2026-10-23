import pandas as pd

from app.engine.indicators import ema, sma
from tests.engine.conftest import candles_df


def test_sma_matches_pandas_rolling_reference():
    closes = candles_df(90)["close"]
    result = sma(closes, 20)
    reference = closes.rolling(window=20, min_periods=20).mean()
    pd.testing.assert_series_equal(result, reference)


def test_sma_is_nan_before_enough_history():
    closes = candles_df(10)["close"]
    result = sma(closes, 20)
    assert result.isna().all()


def test_ema_reacts_faster_than_sma_to_a_recent_jump():
    closes = pd.Series([100.0] * 30 + [200.0] * 5)
    sma_result = sma(closes, 10)
    ema_result = ema(closes, 10)
    assert ema_result.iloc[-1] > sma_result.iloc[-1]
