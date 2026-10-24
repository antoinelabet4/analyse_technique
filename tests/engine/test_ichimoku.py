import pandas as pd

from app.engine.indicators import (
    ICHIMOKU_SHIFT,
    _couleur_nuage,
    _croisement,
    ichimoku,
)


def _candles_plates(n: int, prix: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame({"high": [prix] * n, "low": [prix] * n, "close": [prix] * n})


def test_prix_au_dessus_du_nuage():
    candles = _candles_plates(90)
    candles.loc[candles.index[-1], "close"] = 200.0
    result = ichimoku(candles)
    assert result.prix_vs_nuage == "au_dessus"


def test_prix_en_dessous_du_nuage():
    candles = _candles_plates(90)
    candles.loc[candles.index[-1], "close"] = 50.0
    result = ichimoku(candles)
    assert result.prix_vs_nuage == "en_dessous"


def test_prix_dans_le_nuage():
    candles = _candles_plates(90)
    result = ichimoku(candles)
    assert result.prix_vs_nuage == "dans"


def test_nuage_insuffisant_sur_historique_trop_court():
    candles = _candles_plates(70)
    result = ichimoku(candles)
    assert result.prix_vs_nuage == "insuffisant"
    assert result.nuage_haut_actuel is None
    assert result.nuage_bas_actuel is None


def test_chikou_indisponible_sur_historique_trop_court():
    candles = _candles_plates(20)
    result = ichimoku(candles)
    assert result.chikou_vs_prix_historique == "indisponible"


def test_chikou_au_dessus_du_prix_historique():
    candles = _candles_plates(90)
    candles.loc[candles.index[-1], "close"] = 500.0
    result = ichimoku(candles)
    assert result.chikou_vs_prix_historique == "au_dessus"


def test_croisement_haussier():
    tenkan = pd.Series([9.0, 11.0])
    kijun = pd.Series([10.0, 10.0])
    assert _croisement(tenkan, kijun) == "croisement_haussier"


def test_croisement_baissier():
    tenkan = pd.Series([11.0, 9.0])
    kijun = pd.Series([10.0, 10.0])
    assert _croisement(tenkan, kijun) == "croisement_baissier"


def test_pas_de_croisement():
    tenkan = pd.Series([11.0, 12.0])
    kijun = pd.Series([10.0, 10.0])
    assert _croisement(tenkan, kijun) == "aucun"


def test_couleur_nuage_haussier():
    assert _couleur_nuage(senkou_a=110.0, senkou_b=100.0) == "haussier"


def test_couleur_nuage_baissier():
    assert _couleur_nuage(senkou_a=90.0, senkou_b=100.0) == "baissier"


def test_couleur_nuage_indisponible_si_donnee_manquante():
    assert _couleur_nuage(senkou_a=None, senkou_b=100.0) == "indisponible"


def test_shift_par_defaut_est_26():
    assert ICHIMOKU_SHIFT == 26
