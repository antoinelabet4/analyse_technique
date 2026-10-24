import pandas as pd

from app.engine.indicators import atr, rsi


def test_rsi_is_100_on_a_strictly_increasing_series():
    closes = pd.Series([float(i) for i in range(1, 40)])
    result = rsi(closes, period=14)
    assert result.iloc[-1] == 100.0


def test_rsi_is_0_on_a_strictly_decreasing_series():
    closes = pd.Series([float(i) for i in range(40, 1, -1)])
    result = rsi(closes, period=14)
    assert result.iloc[-1] == 0.0


def test_rsi_is_50_on_a_flat_series():
    closes = pd.Series([100.0] * 30)
    result = rsi(closes, period=14)
    assert result.iloc[-1] == 50.0


def test_atr_is_zero_on_a_perfectly_flat_series():
    candles = pd.DataFrame(
        {
            "high": [100.0] * 30,
            "low": [100.0] * 30,
            "close": [100.0] * 30,
        }
    )
    result = atr(candles, period=14)
    assert result.iloc[-1] == 0.0


def test_atr_is_positive_when_range_is_positive():
    candles = pd.DataFrame(
        {
            "high": [101.0 + i * 0.1 for i in range(30)],
            "low": [99.0 + i * 0.1 for i in range(30)],
            "close": [100.0 + i * 0.1 for i in range(30)],
        }
    )
    result = atr(candles, period=14)
    assert result.iloc[-1] > 0.0
