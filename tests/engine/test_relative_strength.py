import pandas as pd

from app.engine.relative_strength import relative_strength


def test_tendance_hausse_quand_le_ratio_monte():
    closes_btc = pd.Series([100.0] * 40)
    closes_actif = pd.Series([10.0] * 10 + [15.0] * 30)  # ratio passe de 0.10 à 0.15
    result = relative_strength(closes_actif, closes_btc, periode=30)
    assert result.tendance == "hausse"
    assert result.variation_pct_periode > 0


def test_tendance_baisse_quand_le_ratio_descend():
    closes_btc = pd.Series([100.0] * 40)
    closes_actif = pd.Series([15.0] * 10 + [10.0] * 30)
    result = relative_strength(closes_actif, closes_btc, periode=30)
    assert result.tendance == "baisse"
    assert result.variation_pct_periode < 0


def test_tendance_plate_sous_le_seuil_de_1_pourcent():
    closes_btc = pd.Series([100.0] * 40)
    closes_actif = pd.Series([10.0] * 40)
    result = relative_strength(closes_actif, closes_btc, periode=30)
    assert result.tendance == "plat"


def test_indisponible_si_historique_insuffisant():
    closes_btc = pd.Series([100.0] * 5)
    closes_actif = pd.Series([10.0] * 5)
    result = relative_strength(closes_actif, closes_btc, periode=30)
    assert result.tendance == "indisponible"
    assert result.variation_pct_periode is None


def test_indisponible_si_series_de_longueurs_differentes():
    result = relative_strength(pd.Series([1.0, 2.0]), pd.Series([1.0]))
    assert result.tendance == "indisponible"
