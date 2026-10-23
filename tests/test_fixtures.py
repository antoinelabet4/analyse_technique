from app.fixtures import generate_demo_candles


def test_candles_are_internally_consistent():
    candles = generate_demo_candles(days=30)
    assert len(candles) == 30
    for c in candles:
        assert c["high"] >= max(c["open"], c["close"])
        assert c["low"] <= min(c["open"], c["close"])
        assert c["high"] >= c["low"]


def test_candles_are_deterministic():
    assert generate_demo_candles(days=10) == generate_demo_candles(days=10)


def test_candles_dates_increase():
    candles = generate_demo_candles(days=5)
    dates = [c["time"] for c in candles]
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)
