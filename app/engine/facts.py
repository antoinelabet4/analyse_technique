"""Assemble le JSON "facts" pour un actif et un timeframe : seul ce JSON
sera fourni au texte explicatif LLM (phase suivante), jamais le code qui le
produit. Chaque nombre présent ici doit être calculé à partir d'une donnée
réelle ou explicitement marqué indisponible, jamais inventé.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

import pandas as pd

from app.data.derivatives import get_funding_oi, get_options_context
from app.data.macro import get_btc_dominance, get_dxy, get_fear_greed, get_sp500
from app.data.market import get_candles
from app.data.onchain import get_onchain_metrics
from app.engine.cycle import get_btc_cycle_channel
from app.engine.indicators import atr, ema, ichimoku, levels, macd, regime, rsi, scenarios, sma
from app.engine.relative_strength import relative_strength


def _candles_to_df(candles) -> pd.DataFrame:
    return pd.DataFrame([c.__dict__ for c in candles])


def _nombre_ou_none(valeur: Any) -> float | None:
    if valeur is None:
        return None
    try:
        if isinstance(valeur, float) and math.isnan(valeur):
            return None
        if pd.isna(valeur):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(valeur), 6)


def _level_to_dict(level) -> dict:
    d = asdict(level)
    d["prix_haut"] = _nombre_ou_none(d["prix_haut"])
    d["prix_bas"] = _nombre_ou_none(d["prix_bas"])
    return d


def build_facts(asset: str, timeframe: str, candles_limit: int = 1000) -> dict:
    """`candles_limit` élevé par défaut (1000, le maximum par appel Binance)
    pour que le graphique ait assez d'historique pour les boutons de durée
    (1M/3M/6M/YTD/1Y/Tout) sans rappel réseau à chaque clic — ceux-ci ne
    font que zoomer sur les données déjà chargées, côté client."""
    resultat_marche = get_candles(asset, timeframe, limit=candles_limit)
    candles = _candles_to_df(resultat_marche.candles)
    closes = candles["close"]

    atr_series = atr(candles, period=14)
    rsi_series = rsi(closes, period=14)
    macd_result = macd(closes)
    ichimoku_result = ichimoku(candles)

    # Courbes complètes RSI et MACD (pas seulement la valeur actuelle),
    # pour un affichage en sous-graphique sous le graphique principal,
    # demande explicite du propriétaire (25/10/2026).
    rsi_serie = [
        {"time": t, "valeur": _nombre_ou_none(v)}
        for t, v in zip(candles["time"], rsi_series)
        if not pd.isna(v)
    ]
    macd_serie = [
        {"time": t, "ligne": _nombre_ou_none(l), "signal": _nombre_ou_none(s), "histogramme": _nombre_ou_none(h)}
        for t, l, s, h in zip(candles["time"], macd_result.ligne, macd_result.signal, macd_result.histogramme)
        if not (pd.isna(l) or pd.isna(s) or pd.isna(h))
    ]

    if timeframe == "1d":
        mm50_series = sma(closes, 50)
        mm200_series = sma(closes, 200)
        moyennes_mobiles = {
            "mm50": _nombre_ou_none(mm50_series.iloc[-1]),
            "mm200": _nombre_ou_none(mm200_series.iloc[-1]),
        }
        mm_longue = mm200_series
        series_moyennes_mobiles = {"mm50": mm50_series, "mm200": mm200_series}
    else:
        ema200_series = ema(closes, 200)
        moyennes_mobiles = {"ema200": _nombre_ou_none(ema200_series.iloc[-1])}
        mm_longue = ema200_series
        series_moyennes_mobiles = {"ema200": ema200_series}

    # Courbe complète (pas seulement la valeur actuelle) pour que le
    # graphique affiche les moyennes mobiles comme une vraie ligne qui suit
    # le prix dans le temps, demande explicite du propriétaire (24/10/2026).
    moyennes_mobiles_serie = {
        nom: [
            {"time": t, "valeur": _nombre_ou_none(v)}
            for t, v in zip(candles["time"], serie)
            if not pd.isna(v)
        ]
        for nom, serie in series_moyennes_mobiles.items()
    }

    nuage_serie = [
        {"time": t, "senkou_a": _nombre_ou_none(a), "senkou_b": _nombre_ou_none(b)}
        for t, a, b in zip(candles["time"], ichimoku_result.senkou_a, ichimoku_result.senkou_b)
        if not (pd.isna(a) or pd.isna(b))
    ]

    niveaux = levels(candles, atr_series, ichimoku_result)
    regime_result = regime(candles, mm_longue, ichimoku_result)
    scenarios_list = scenarios(candles, niveaux, ichimoku_result, timeframe)

    force_relative = None
    if asset != "BTC":
        try:
            btc = get_candles("BTC", timeframe)
            btc_df = _candles_to_df(btc.candles)
            fusion = pd.merge(candles[["time", "close"]], btc_df[["time", "close"]], on="time", suffixes=("_actif", "_btc"))
            if len(fusion) > 1:
                fr = relative_strength(fusion["close_actif"], fusion["close_btc"])
                force_relative = {
                    "ratio_actuel": _nombre_ou_none(fr.ratio_actuel),
                    "tendance": fr.tendance,
                    "variation_pct_periode": _nombre_ou_none(fr.variation_pct_periode),
                }
        except Exception:
            # Aucune donnée inventée : si le contexte BTC n'est pas
            # disponible, le champ reste explicitement absent (None),
            # jamais une estimation.
            force_relative = None

    # Dérivés et macro : chaque source gère déjà son propre échec en
    # interne (disponible=False + raison), mais on isole quand même ici
    # pour qu'un bug imprévu dans ces modules ne casse jamais l'affichage
    # du moteur déterministe principal.
    try:
        derives = {
            "funding_oi": asdict(get_funding_oi(asset)),
            "options": asdict(get_options_context(asset)),
        }
    except Exception:
        derives = {
            "funding_oi": {"disponible": False, "raison": "erreur interne"},
            "options": {"disponible": False, "raison": "erreur interne"},
        }

    try:
        macro = {
            "fear_greed": asdict(get_fear_greed()),
            "dominance_btc": asdict(get_btc_dominance()),
            "sp500": asdict(get_sp500()),
            "dxy": asdict(get_dxy()),
        }
    except Exception:
        indisponible = {"disponible": False, "raison": "erreur interne"}
        macro = {"fear_greed": indisponible, "dominance_btc": indisponible, "sp500": indisponible, "dxy": indisponible}

    # On-chain et canal de cycle : source centrée BTC uniquement (comme le
    # reste de la méthode), null pour les autres actifs plutôt qu'une
    # valeur approximative.
    onchain = None
    cycle = None
    if asset == "BTC":
        try:
            onchain = asdict(get_onchain_metrics())
        except Exception:
            onchain = {"disponible": False, "raison": "erreur interne"}
        try:
            cycle = asdict(get_btc_cycle_channel())
        except Exception:
            cycle = {"disponible": False, "raison": "erreur interne"}

    return {
        "actif": asset,
        "timeframe": timeframe,
        "source": resultat_marche.source,
        "a_jour_le": resultat_marche.a_jour_le,
        "perime": resultat_marche.perime,
        "prix_actuel": _nombre_ou_none(closes.iloc[-1]),
        "moyennes_mobiles": moyennes_mobiles,
        "moyennes_mobiles_serie": moyennes_mobiles_serie,
        "rsi14": _nombre_ou_none(rsi_series.iloc[-1]),
        "rsi_serie": rsi_serie,
        "atr14": _nombre_ou_none(atr_series.iloc[-1]),
        "macd": {
            "ligne": _nombre_ou_none(macd_result.ligne.iloc[-1]),
            "signal": _nombre_ou_none(macd_result.signal.iloc[-1]),
            "histogramme": _nombre_ou_none(macd_result.histogramme.iloc[-1]),
            "serie": macd_serie,
        },
        "ichimoku": {
            "tenkan": _nombre_ou_none(ichimoku_result.tenkan_actuel),
            "kijun": _nombre_ou_none(ichimoku_result.kijun_actuel),
            "nuage_haut": _nombre_ou_none(ichimoku_result.nuage_haut_actuel),
            "nuage_bas": _nombre_ou_none(ichimoku_result.nuage_bas_actuel),
            "prix_vs_nuage": ichimoku_result.prix_vs_nuage,
            "couleur_nuage": ichimoku_result.couleur_nuage,
            "tenkan_vs_kijun": ichimoku_result.tenkan_vs_kijun,
            "chikou_vs_prix_historique": ichimoku_result.chikou_vs_prix_historique,
            "nuage_serie": nuage_serie,
        },
        "niveaux": [_level_to_dict(l) for l in niveaux],
        "regime": asdict(regime_result),
        "scenarios": [asdict(s) for s in scenarios_list],
        "force_relative_btc": force_relative,
        "derives": derives,
        "macro": macro,
        "onchain": onchain,
        "cycle": cycle,
        "candles": candles.to_dict(orient="records"),
    }
