"""Contrôle automatique : aucun nombre du texte explicatif ne doit être
absent du JSON "facts" fourni au LLM. Fonctions pures, aucun I/O.

Voir docs/specs-techniques/P1-texte-explicatif-llm.md.
"""
from __future__ import annotations

import re

# Constantes de période des indicateurs (ex. "RSI14", "MM200"), pas des
# données de marché : exemptées du contrôle pour éviter un faux négatif
# quand le texte les mentionne (ex. "RSI 14 à 43,82").
PERIODES_INDICATEURS_EXEMPTEES = {9, 14, 26, 50, 52, 200}

# Arrondir a 2 decimales a l'extraction perdait toute precision utile
# pour les actifs a tres faible valeur unitaire (ex. SHIB ~0,000005) :
# un nombre reel des facts et un chiffre invente par le LLM devenaient
# tous les deux "0.0", le controle ne detectait plus rien pour ces
# actifs (bug trouve le 25/10/2026, liste des actifs etendue a 22
# cryptos). 10 decimales couvrent les deux echelles (BTC et SHIB) sans
# changer le comportement pour les prix "normaux" : la comparaison
# "assez proche" reste de toute facon geree par _tolerance ci-dessous,
# cet arrondi ne sert qu'a neutraliser le bruit de virgule flottante.
_DECIMALES_EXTRACTION = 10

# Le lookbehind négatif (?<!\d) évite de lire le tiret séparateur d'une
# date ISO ("2026-10-25") comme un signe moins : sans lui, cette date
# produisait les nombres -10 et -25, jamais présents dans les facts
# numériques, ce qui rejetait à tort le texte généré (bug réel trouvé
# en production le 25/10/2026). Un "-" précédé d'un espace ou en début
# de chaîne (ex. "une baisse de -5 %") reste bien interprété comme un
# signe moins.
_NOMBRE_RE = re.compile(r"(?<!\d)-?\d[\d\s ]*(?:[.,]\d+)?")


def _extraire_nombres_facts(facts) -> set[float]:
    nombres: set[float] = set()

    def visiter(valeur):
        if isinstance(valeur, bool):
            return
        if isinstance(valeur, (int, float)):
            nombres.add(round(float(valeur), _DECIMALES_EXTRACTION))
        elif isinstance(valeur, str):
            # Une chaîne (ex. une date ISO "a_jour_le": "2026-10-25T...")
            # peut contenir des chiffres légitimes que le texte explicatif
            # reprend sans les inventer (bug trouvé le 25/10/2026 en
            # production : "2026" rejeté comme chiffre absent des données
            # alors qu'il apparaît bien dans une date du JSON "facts").
            for m in _NOMBRE_RE.finditer(valeur):
                brut = m.group().replace(" ", "").replace(" ", "").replace(",", ".")
                try:
                    nombres.add(round(float(brut), _DECIMALES_EXTRACTION))
                except ValueError:
                    continue
        elif isinstance(valeur, dict):
            for v in valeur.values():
                visiter(v)
        elif isinstance(valeur, list):
            for v in valeur:
                visiter(v)

    visiter(facts)
    return nombres


def _extraire_nombres_texte(texte: str) -> set[float]:
    nombres: set[float] = set()
    for m in _NOMBRE_RE.finditer(texte):
        brut = m.group().replace(" ", "").replace(" ", "").replace(",", ".")
        try:
            valeur = float(brut)
        except ValueError:
            continue
        if valeur in PERIODES_INDICATEURS_EXEMPTEES:
            continue
        nombres.add(round(valeur, _DECIMALES_EXTRACTION))
    return nombres


def _tolerance(nf: float) -> float:
    # Le plancher fixe de 0.01 posait le meme probleme que l'arrondi a
    # l'extraction : beaucoup trop large pour un actif a 0,000005, il
    # aurait accepte n'importe quel petit chiffre invente comme "assez
    # proche" de zero. Plancher proportionnel a l'echelle du nombre
    # compare plutot qu'une valeur absolue unique.
    abs_nf = abs(nf)
    if abs_nf >= 1:
        plancher = 0.01
    elif abs_nf >= 0.01:
        plancher = 0.0001
    elif abs_nf >= 0.0001:
        plancher = 0.000001
    else:
        plancher = 0.00000001
    return max(plancher, abs_nf * 0.005)


def tous_les_nombres_sont_dans_facts(texte: str, facts: dict) -> tuple[bool, list[float]]:
    """Retourne (conforme, nombres_du_texte_absents_des_facts)."""
    nombres_facts = _extraire_nombres_facts(facts)
    nombres_texte = _extraire_nombres_texte(texte)
    manquants = [
        n for n in nombres_texte
        if not any(abs(n - nf) <= _tolerance(nf) for nf in nombres_facts)
    ]
    return (len(manquants) == 0, sorted(manquants))
