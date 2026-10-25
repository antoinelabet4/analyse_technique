"""Moteur déterministe d'indicateurs, niveaux, régime et scénarios.

Aucun appel réseau ni appel LLM ici : toutes les fonctions sont pures,
elles ne font que calculer à partir des bougies passées en entrée. Voir
docs/specs-techniques/P1-moteur-indicateurs.md pour le détail des règles.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Réglages Ichimoku classiques (méthode japonaise d'origine). Point ouvert :
# aucun paramétrage spécifique à la méthode de Vincent Ganne n'a pu être
# confirmé ; voir le statut de la spec associée.
ICHIMOKU_TENKAN_PERIOD = 9
ICHIMOKU_KIJUN_PERIOD = 26
ICHIMOKU_SENKOU_B_PERIOD = 52
ICHIMOKU_SHIFT = 26


# --------------------------------------------------------------------------
# Moyennes mobiles, RSI, ATR
# --------------------------------------------------------------------------


def sma(closes: pd.Series, period: int) -> pd.Series:
    return closes.rolling(window=period, min_periods=period).mean()


def ema(closes: pd.Series, period: int) -> pd.Series:
    return closes.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """RSI de Wilder (lissage exponentiel alpha = 1/period)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.where(avg_loss != 0, 100.0)
    result = result.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return result


def atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR de Wilder (true range lissé en exponentiel)."""
    high, low, close = candles["high"], candles["low"], candles["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


# Réglages MACD classiques (12/26/9). Même point ouvert que pour
# l'Ichimoku ci-dessus : aucun paramétrage spécifique à la méthode de
# Vincent Ganne n'a pu être confirmé pour le MACD.
MACD_RAPIDE_PERIOD = 12
MACD_LENT_PERIOD = 26
MACD_SIGNAL_PERIOD = 9


@dataclass
class MACDResult:
    ligne: pd.Series
    signal: pd.Series
    histogramme: pd.Series


def macd(
    closes: pd.Series,
    rapide: int = MACD_RAPIDE_PERIOD,
    lent: int = MACD_LENT_PERIOD,
    signal_period: int = MACD_SIGNAL_PERIOD,
) -> MACDResult:
    """MACD (Moving Average Convergence Divergence) : ligne = EMA rapide -
    EMA lente, signal = EMA de la ligne, histogramme = ligne - signal."""
    ligne = ema(closes, rapide) - ema(closes, lent)
    signal = ligne.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    histogramme = ligne - signal
    return MACDResult(ligne=ligne, signal=signal, histogramme=histogramme)


# --------------------------------------------------------------------------
# Ichimoku Kinko Hyo
# --------------------------------------------------------------------------


@dataclass
class IchimokuResult:
    tenkan: pd.Series
    kijun: pd.Series
    senkou_a: pd.Series
    senkou_b: pd.Series
    chikou: pd.Series
    tenkan_actuel: float | None
    kijun_actuel: float | None
    nuage_haut_actuel: float | None
    nuage_bas_actuel: float | None
    prix_vs_nuage: str
    couleur_nuage: str
    tenkan_vs_kijun: str
    chikou_vs_prix_historique: str


def ichimoku(
    candles: pd.DataFrame,
    tenkan_period: int = ICHIMOKU_TENKAN_PERIOD,
    kijun_period: int = ICHIMOKU_KIJUN_PERIOD,
    senkou_b_period: int = ICHIMOKU_SENKOU_B_PERIOD,
    shift: int = ICHIMOKU_SHIFT,
) -> IchimokuResult:
    high, low, close = candles["high"], candles["low"], candles["close"]

    def midpoint(period: int) -> pd.Series:
        return (high.rolling(period).max() + low.rolling(period).min()) / 2

    tenkan = midpoint(tenkan_period)
    kijun = midpoint(kijun_period)
    senkou_a_raw = (tenkan + kijun) / 2
    senkou_b_raw = midpoint(senkou_b_period)

    # Décalées vers l'avant : la valeur du nuage "actif aujourd'hui" a été
    # calculée `shift` périodes plus tôt. Projeter le nuage au-delà de la
    # dernière bougie (pour l'affichage graphique) est hors périmètre de ce
    # module, qui ne restitue que les lectures à la date courante.
    senkou_a = senkou_a_raw.shift(shift)
    senkou_b = senkou_b_raw.shift(shift)
    chikou = close.shift(-shift)

    tenkan_actuel = _dernier_ou_none(tenkan)
    kijun_actuel = _dernier_ou_none(kijun)
    senkou_a_actuel = _dernier_ou_none(senkou_a)
    senkou_b_actuel = _dernier_ou_none(senkou_b)
    # Le nuage n'est disponible que si SES DEUX bornes le sont : une seule
    # borne valide ne doit jamais produire une lecture partielle silencieuse.
    if senkou_a_actuel is None or senkou_b_actuel is None:
        nuage_haut_actuel = None
        nuage_bas_actuel = None
    else:
        nuage_haut_actuel = max(senkou_a_actuel, senkou_b_actuel)
        nuage_bas_actuel = min(senkou_a_actuel, senkou_b_actuel)

    prix_vs_nuage = _prix_vs_nuage(close.iloc[-1], nuage_haut_actuel, nuage_bas_actuel)
    couleur_nuage = _couleur_nuage(senkou_a_actuel, senkou_b_actuel)
    tenkan_vs_kijun = _croisement(tenkan, kijun)
    chikou_vs_prix_historique = _chikou_vs_prix_historique(close, shift)

    return IchimokuResult(
        tenkan=tenkan,
        kijun=kijun,
        senkou_a=senkou_a,
        senkou_b=senkou_b,
        chikou=chikou,
        tenkan_actuel=tenkan_actuel,
        kijun_actuel=kijun_actuel,
        nuage_haut_actuel=nuage_haut_actuel,
        nuage_bas_actuel=nuage_bas_actuel,
        prix_vs_nuage=prix_vs_nuage,
        couleur_nuage=couleur_nuage,
        tenkan_vs_kijun=tenkan_vs_kijun,
        chikou_vs_prix_historique=chikou_vs_prix_historique,
    )


def _dernier_ou_none(serie: pd.Series) -> float | None:
    if len(serie) == 0 or pd.isna(serie.iloc[-1]):
        return None
    return float(serie.iloc[-1])


def _prix_vs_nuage(prix: float, nuage_haut: float | None, nuage_bas: float | None) -> str:
    if nuage_haut is None or nuage_bas is None:
        return "insuffisant"
    if prix > nuage_haut:
        return "au_dessus"
    if prix < nuage_bas:
        return "en_dessous"
    return "dans"


def _couleur_nuage(senkou_a: float | None, senkou_b: float | None) -> str:
    if senkou_a is None or senkou_b is None:
        return "indisponible"
    if senkou_a > senkou_b:
        return "haussier"
    if senkou_a < senkou_b:
        return "baissier"
    return "neutre"


def _croisement(tenkan: pd.Series, kijun: pd.Series) -> str:
    if len(tenkan) < 2:
        return "aucun"
    t_prev, t_now = tenkan.iloc[-2], tenkan.iloc[-1]
    k_prev, k_now = kijun.iloc[-2], kijun.iloc[-1]
    if pd.isna(t_prev) or pd.isna(t_now) or pd.isna(k_prev) or pd.isna(k_now):
        return "aucun"
    diff_prev, diff_now = t_prev - k_prev, t_now - k_now
    if diff_prev <= 0 < diff_now:
        return "croisement_haussier"
    if diff_prev >= 0 > diff_now:
        return "croisement_baissier"
    return "aucun"


def _chikou_vs_prix_historique(close: pd.Series, shift: int) -> str:
    if len(close) <= shift:
        return "indisponible"
    prix_actuel = close.iloc[-1]
    prix_historique = close.iloc[-1 - shift]
    if prix_actuel > prix_historique:
        return "au_dessus"
    if prix_actuel < prix_historique:
        return "en_dessous"
    return "egal"


# --------------------------------------------------------------------------
# Niveaux (pivots + nuage)
# --------------------------------------------------------------------------


@dataclass
class Level:
    prix_haut: float
    prix_bas: float
    type: str  # "pivot" | "nuage"
    touches: int | None = None
    role_inverse: bool = False
    est_record_historique: bool = False


def find_pivots(candles: pd.DataFrame, window: int = 3) -> tuple[list[float], list[float]]:
    """Détection de swing highs/lows simple (extremum local sur `window` bougies de part et d'autre)."""
    highs, lows = candles["high"], candles["low"]
    n = len(candles)
    swing_highs: list[float] = []
    swing_lows: list[float] = []
    for i in range(window, n - window):
        fenetre_haut = highs.iloc[i - window : i + window + 1]
        fenetre_bas = lows.iloc[i - window : i + window + 1]
        if highs.iloc[i] == fenetre_haut.max():
            swing_highs.append(float(highs.iloc[i]))
        if lows.iloc[i] == fenetre_bas.min():
            swing_lows.append(float(lows.iloc[i]))
    return swing_highs, swing_lows


def _group_into_zones(pivots: list[float], tolerance: float) -> list[Level]:
    if not pivots:
        return []
    pivots_tries = sorted(pivots)
    zones: list[list[float]] = [[pivots_tries[0]]]
    for prix in pivots_tries[1:]:
        if prix - zones[-1][-1] <= tolerance:
            zones[-1].append(prix)
        else:
            zones.append([prix])
    return [
        Level(prix_haut=max(zone), prix_bas=min(zone), type="pivot", touches=len(zone))
        for zone in zones
    ]


def _detecter_inversion_role(level: Level, candles: pd.DataFrame) -> bool:
    """Heuristique simple : la zone a-t-elle été support puis résistance (ou l'inverse)
    entre la première et la deuxième moitié de l'historique fourni ?"""
    closes = candles["close"]
    moitie = len(closes) // 2
    if moitie < 5:
        return False
    premiere, seconde = closes.iloc[:moitie], closes.iloc[moitie:]
    recente = seconde.iloc[-5:] if len(seconde) >= 5 else seconde

    etait_au_dessus = (premiere > level.prix_haut).mean() > 0.5
    etait_en_dessous = (premiere < level.prix_bas).mean() > 0.5
    est_maintenant_en_dessous = (recente < level.prix_bas).mean() > 0.5
    est_maintenant_au_dessus = (recente > level.prix_haut).mean() > 0.5

    return bool(
        (etait_au_dessus and est_maintenant_en_dessous)
        or (etait_en_dessous and est_maintenant_au_dessus)
    )


def levels(
    candles: pd.DataFrame,
    atr_series: pd.Series,
    ichimoku_result: IchimokuResult,
    window: int = 3,
    atr_tolerance_mult: float = 1.0,
    max_per_side: int = 3,
) -> list[Level]:
    swing_highs, swing_lows = find_pivots(candles, window=window)
    dernier_atr = atr_series.iloc[-1] if not pd.isna(atr_series.iloc[-1]) else 0.0
    tolerance = dernier_atr * atr_tolerance_mult

    zones = _group_into_zones(swing_highs + swing_lows, tolerance)

    record_historique = float(candles["high"].max())
    for zone in zones:
        zone.role_inverse = _detecter_inversion_role(zone, candles)
        zone.est_record_historique = zone.prix_haut >= record_historique

    if ichimoku_result.nuage_haut_actuel is not None and ichimoku_result.nuage_bas_actuel is not None:
        zones.append(
            Level(
                prix_haut=ichimoku_result.nuage_haut_actuel,
                prix_bas=ichimoku_result.nuage_bas_actuel,
                type="nuage",
            )
        )

    prix_courant = float(candles["close"].iloc[-1])
    supports = sorted(
        (z for z in zones if z.prix_haut <= prix_courant),
        key=lambda z: prix_courant - z.prix_haut,
    )[:max_per_side]
    resistances = sorted(
        (z for z in zones if z.prix_bas >= prix_courant),
        key=lambda z: z.prix_bas - prix_courant,
    )[:max_per_side]

    return supports + resistances


# --------------------------------------------------------------------------
# Régime de marché
# --------------------------------------------------------------------------


@dataclass
class Regime:
    prix_vs_mm_longue: str  # "au_dessus" | "en_dessous" | "egal" | "indisponible"
    pente_mm_longue: str  # "haussiere" | "baissiere" | "plate" | "indisponible"
    structure: str  # "hausse" | "baisse" | "range" | "indetermine"
    ichimoku_prix_vs_nuage: str
    ichimoku_couleur_nuage: str
    ichimoku_tenkan_vs_kijun: str


def detect_structure(candles: pd.DataFrame, window: int = 3) -> str:
    """Heuristique simple sur les 2 derniers pivots : tendance de la structure
    de sommets/creux, pas une détection robuste de figure chartiste."""
    swing_highs, swing_lows = find_pivots(candles, window=window)
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "indetermine"
    hauts_en_hausse = swing_highs[-1] > swing_highs[-2]
    bas_en_hausse = swing_lows[-1] > swing_lows[-2]
    if hauts_en_hausse and bas_en_hausse:
        return "hausse"
    if not hauts_en_hausse and not bas_en_hausse:
        return "baisse"
    return "range"


def regime(candles: pd.DataFrame, mm_longue: pd.Series, ichimoku_result: IchimokuResult) -> Regime:
    """`mm_longue` est la moyenne mobile de référence du régime (MM200 en 1D, EMA200 en 1W)."""
    close = float(candles["close"].iloc[-1])
    derniere_mm = mm_longue.iloc[-1]

    if pd.isna(derniere_mm):
        prix_vs_mm_longue = "indisponible"
        pente_mm_longue = "indisponible"
    else:
        if close > derniere_mm:
            prix_vs_mm_longue = "au_dessus"
        elif close < derniere_mm:
            prix_vs_mm_longue = "en_dessous"
        else:
            prix_vs_mm_longue = "egal"

        mm_valide = mm_longue.dropna()
        if len(mm_valide) >= 2:
            diff = mm_valide.iloc[-1] - mm_valide.iloc[-2]
            pente_mm_longue = "haussiere" if diff > 0 else "baissiere" if diff < 0 else "plate"
        else:
            pente_mm_longue = "indisponible"

    return Regime(
        prix_vs_mm_longue=prix_vs_mm_longue,
        pente_mm_longue=pente_mm_longue,
        structure=detect_structure(candles),
        ichimoku_prix_vs_nuage=ichimoku_result.prix_vs_nuage,
        ichimoku_couleur_nuage=ichimoku_result.couleur_nuage,
        ichimoku_tenkan_vs_kijun=ichimoku_result.tenkan_vs_kijun,
    )


# --------------------------------------------------------------------------
# Scénarios
# --------------------------------------------------------------------------


@dataclass
class Scenario:
    type: str  # "haussier" | "baissier" | "range"
    condition_cloture: str
    cible: float | None
    invalidation: float | None
    source_invalidation: str | None  # "support_proche" | "resistance_proche" | "kijun" | None


def _invalidation_sous_le_prix(
    prix: float, supports: list[Level], ichimoku_result: IchimokuResult
) -> tuple[float | None, str | None]:
    candidats: list[tuple[float, str]] = []
    if supports:
        candidats.append((supports[0].prix_bas, "support_proche"))
    if ichimoku_result.kijun_actuel is not None and ichimoku_result.kijun_actuel < prix:
        candidats.append((ichimoku_result.kijun_actuel, "kijun"))
    if not candidats:
        return None, None
    return max(candidats, key=lambda c: c[0])


def _invalidation_au_dessus_du_prix(
    prix: float, resistances: list[Level], ichimoku_result: IchimokuResult
) -> tuple[float | None, str | None]:
    candidats: list[tuple[float, str]] = []
    if resistances:
        candidats.append((resistances[0].prix_haut, "resistance_proche"))
    if ichimoku_result.kijun_actuel is not None and ichimoku_result.kijun_actuel > prix:
        candidats.append((ichimoku_result.kijun_actuel, "kijun"))
    if not candidats:
        return None, None
    return min(candidats, key=lambda c: c[0])


def scenarios(
    candles: pd.DataFrame,
    levels_list: list[Level],
    ichimoku_result: IchimokuResult,
    timeframe: str,
) -> list[Scenario]:
    prix = float(candles["close"].iloc[-1])
    unite = "journalière" if timeframe == "1d" else "hebdomadaire"

    supports = sorted(
        (l for l in levels_list if l.prix_haut <= prix), key=lambda l: prix - l.prix_haut
    )
    resistances = sorted(
        (l for l in levels_list if l.prix_bas >= prix), key=lambda l: l.prix_bas - prix
    )

    cible_haussiere = resistances[0].prix_bas if resistances else None
    cible_baissiere = supports[0].prix_haut if supports else None
    invalidation_haussiere, source_haussiere = _invalidation_sous_le_prix(
        prix, supports, ichimoku_result
    )
    invalidation_baissiere, source_baissiere = _invalidation_au_dessus_du_prix(
        prix, resistances, ichimoku_result
    )

    scenario_haussier = Scenario(
        type="haussier",
        condition_cloture=(
            f"Clôture {unite} au-dessus de {cible_haussiere}"
            if cible_haussiere is not None
            else "Aucune résistance identifiée au-dessus du prix actuel"
        ),
        cible=cible_haussiere,
        invalidation=invalidation_haussiere,
        source_invalidation=source_haussiere,
    )
    scenario_baissier = Scenario(
        type="baissier",
        condition_cloture=(
            f"Clôture {unite} en dessous de {cible_baissiere}"
            if cible_baissiere is not None
            else "Aucun support identifié en dessous du prix actuel"
        ),
        cible=cible_baissiere,
        invalidation=invalidation_baissiere,
        source_invalidation=source_baissiere,
    )
    scenario_range = Scenario(
        type="range",
        condition_cloture=(
            f"Prix maintenu entre {supports[0].prix_haut} et {resistances[0].prix_bas}"
            if supports and resistances
            else "Bornes de range indisponibles (support ou résistance manquant)"
        ),
        cible=None,
        invalidation=None,
        source_invalidation=None,
    )
    return [scenario_haussier, scenario_baissier, scenario_range]
