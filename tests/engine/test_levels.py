import pandas as pd

from app.engine.indicators import Level, _detecter_inversion_role, _group_into_zones, atr, find_pivots, ichimoku, levels
from tests.engine.conftest import candles_df


def test_find_pivots_detects_a_clear_swing_high_and_low():
    # index:        0    1    2    3    4    5    6
    highs = [100, 101, 102, 110, 102, 101, 100]
    lows = [90, 89, 88, 80, 88, 89, 90]
    candles = pd.DataFrame({"high": highs, "low": lows, "close": highs})
    swing_highs, swing_lows = find_pivots(candles, window=3)
    assert swing_highs == [110]
    assert swing_lows == [80]


def test_group_into_zones_merges_prices_within_tolerance():
    zones = _group_into_zones([100.0, 100.5, 101.0, 150.0], tolerance=1.0)
    assert len(zones) == 2
    assert zones[0].prix_bas == 100.0
    assert zones[0].prix_haut == 101.0
    assert zones[0].touches == 3
    assert zones[1].prix_bas == zones[1].prix_haut == 150.0


def test_group_into_zones_keeps_prices_separate_beyond_tolerance():
    zones = _group_into_zones([100.0, 110.0, 120.0], tolerance=1.0)
    assert len(zones) == 3


def test_group_into_zones_does_not_chain_a_long_trend_into_one_giant_zone():
    # Bug réel du 25/10/2026 : une suite de pivots proches deux à deux (gap
    # de 1.0, tolérance 1.0) ne doit jamais se chaîner en une seule zone
    # couvrant 100 à 105 — chaque zone doit rester bornée par la tolérance.
    zones = _group_into_zones([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], tolerance=1.0)
    assert len(zones) == 3
    for zone in zones:
        assert zone.prix_haut - zone.prix_bas <= 1.0


def test_role_reversal_detected_when_price_flips_side():
    level = Level(prix_haut=105.0, prix_bas=95.0, type="pivot")
    closes = pd.Series([150.0] * 20 + [100.0] * 15 + [50.0] * 5)
    candles = pd.DataFrame({"close": closes})
    assert _detecter_inversion_role(level, candles) is True


def test_no_role_reversal_when_price_stays_on_the_same_side():
    level = Level(prix_haut=105.0, prix_bas=95.0, type="pivot")
    closes = pd.Series([150.0] * 40)
    candles = pd.DataFrame({"close": closes})
    assert _detecter_inversion_role(level, candles) is False


def test_levels_includes_the_cloud_as_a_level_of_type_nuage():
    candles = candles_df(90)
    atr_series = atr(candles)
    ichimoku_result = ichimoku(candles)
    result = levels(candles, atr_series, ichimoku_result)
    assert any(level.type == "nuage" for level in result)


def test_levels_respects_max_per_side():
    # Le nuage est ajouté à part du classement par distance des pivots
    # (voir test_levels_includes_the_cloud_as_a_level_of_type_nuage) : il
    # ne compte pas dans le plafond max_per_side, qui ne s'applique qu'aux
    # niveaux de type "pivot".
    candles = candles_df(90)
    atr_series = atr(candles)
    ichimoku_result = ichimoku(candles)
    result = levels(candles, atr_series, ichimoku_result, max_per_side=3)
    prix = float(candles["close"].iloc[-1])
    supports = [l for l in result if l.type == "pivot" and l.prix_haut <= prix]
    resistances = [l for l in result if l.type == "pivot" and l.prix_bas >= prix]
    assert len(supports) <= 3
    assert len(resistances) <= 3
