import pandas as pd

from app.engine.indicators import IchimokuResult, Level, scenarios


def _ichimoku_sans_kijun() -> IchimokuResult:
    vide = pd.Series(dtype=float)
    return IchimokuResult(
        tenkan=vide,
        kijun=vide,
        senkou_a=vide,
        senkou_b=vide,
        chikou=vide,
        tenkan_actuel=None,
        kijun_actuel=None,
        nuage_haut_actuel=None,
        nuage_bas_actuel=None,
        prix_vs_nuage="insuffisant",
        couleur_nuage="indisponible",
        tenkan_vs_kijun="aucun",
        chikou_vs_prix_historique="indisponible",
    )


def test_scenario_haussier_vise_la_resistance_la_plus_proche():
    candles = pd.DataFrame({"close": [100.0]})
    levels_list = [
        Level(prix_haut=90.0, prix_bas=85.0, type="pivot"),
        Level(prix_haut=120.0, prix_bas=110.0, type="pivot"),
        Level(prix_haut=150.0, prix_bas=140.0, type="pivot"),
    ]
    result = scenarios(candles, levels_list, _ichimoku_sans_kijun(), timeframe="1d")
    haussier = next(s for s in result if s.type == "haussier")
    assert haussier.cible == 110.0


def test_scenario_baissier_vise_le_support_le_plus_proche():
    candles = pd.DataFrame({"close": [100.0]})
    levels_list = [
        Level(prix_haut=90.0, prix_bas=85.0, type="pivot"),
        Level(prix_haut=80.0, prix_bas=70.0, type="pivot"),
    ]
    result = scenarios(candles, levels_list, _ichimoku_sans_kijun(), timeframe="1d")
    baissier = next(s for s in result if s.type == "baissier")
    assert baissier.cible == 90.0


def test_invalidation_haussiere_utilise_le_support_le_plus_proche_par_defaut():
    candles = pd.DataFrame({"close": [100.0]})
    levels_list = [Level(prix_haut=90.0, prix_bas=85.0, type="pivot")]
    result = scenarios(candles, levels_list, _ichimoku_sans_kijun(), timeframe="1d")
    haussier = next(s for s in result if s.type == "haussier")
    assert haussier.invalidation == 85.0
    assert haussier.source_invalidation == "support_proche"


def test_invalidation_haussiere_prefere_le_kijun_si_plus_proche_du_prix():
    candles = pd.DataFrame({"close": [100.0]})
    levels_list = [Level(prix_haut=90.0, prix_bas=80.0, type="pivot")]
    ichimoku_result = _ichimoku_sans_kijun()
    ichimoku_result.kijun_actuel = 95.0  # plus proche du prix que le support à 80
    result = scenarios(candles, levels_list, ichimoku_result, timeframe="1d")
    haussier = next(s for s in result if s.type == "haussier")
    assert haussier.invalidation == 95.0
    assert haussier.source_invalidation == "kijun"


def test_cibles_et_invalidations_correspondent_toujours_a_un_niveau_fourni():
    candles = pd.DataFrame({"close": [100.0]})
    levels_list = [
        Level(prix_haut=90.0, prix_bas=85.0, type="pivot"),
        Level(prix_haut=120.0, prix_bas=110.0, type="nuage"),
    ]
    prix_connus = {l.prix_haut for l in levels_list} | {l.prix_bas for l in levels_list}
    result = scenarios(candles, levels_list, _ichimoku_sans_kijun(), timeframe="1d")
    for scenario in result:
        if scenario.cible is not None:
            assert scenario.cible in prix_connus
        if scenario.invalidation is not None:
            assert scenario.invalidation in prix_connus


def test_pas_de_scenario_sans_niveaux():
    candles = pd.DataFrame({"close": [100.0]})
    result = scenarios(candles, [], _ichimoku_sans_kijun(), timeframe="1w")
    haussier = next(s for s in result if s.type == "haussier")
    baissier = next(s for s in result if s.type == "baissier")
    assert haussier.cible is None
    assert baissier.cible is None
    assert "hebdomadaire" not in haussier.condition_cloture  # pas de condition car pas de cible
