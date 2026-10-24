# UI — Sélecteur de durée affichée + bouton d'analyse sous le graphique

## Objectif

Deux demandes explicites du propriétaire, envoyées coup sur coup pendant
le développement : pouvoir régler la durée affichée du graphique (1M,
3M, 6M, YTD, 1Y, Tout, comme les sélecteurs de période d'une app
boursière) ; et faire en sorte que le graphique s'affiche toujours, même
sans avoir lancé d'analyse, avec le bouton "Lancer l'analyse" positionné
sous le graphique plutôt qu'en superposition flottante dessus.

## Périmètre

- Inclus :
  - Rangée de boutons de durée (1M/3M/6M/YTD/1Y/Tout) sous le graphique,
    zoom purement côté client sur les bougies déjà chargées (aucun
    nouvel appel réseau par clic).
  - Augmentation de l'historique chargé par défaut (300 → 1000 bougies,
    le maximum par appel Binance) pour que les boutons de durée aient
    assez de recul sans rappel réseau.
  - Réduction du JSON envoyé au LLM (retrait des bougies et de la série
    du nuage Ichimoku, inutiles au texte qualitatif) pour ne pas
    augmenter le coût par appel avec ce nouvel historique plus large —
    le contrôle automatique des chiffres et la clé de cache continuent
    d'utiliser le JSON complet.
  - Repositionnement du bouton "Lancer l'analyse" : bloc normal sous la
    rangée de durées, au lieu d'une pastille en superposition absolue
    sur le bas du graphique.
  - Le graphique se charge et s'affiche dès l'arrivée sur la page, qu'une
    analyse LLM ait été lancée ou non (déjà le comportement existant,
    confirmé par ce lot : `chargerAnalyse()` est appelée indépendamment
    du bouton d'analyse).
  - La durée sélectionnée est conservée lors d'un changement d'actif ou
    de timeframe (elle n'est pas réinitialisée sur "Tout" à chaque
    rechargement de données).
  - Les nouveaux éléments (rangée de durées, bouton d'analyse) sont
    masqués en mode plein écran, comme le reste de l'interface
    secondaire.
- Non inclus : persistance de la durée sélectionnée entre deux visites
  (pas de localStorage pour ce réglage, contrairement aux indicateurs) —
  non demandé, "Tout" reste le défaut à l'ouverture.

## État d'avancement

**Fait — 24/10/2026.**

## Critères de validation

- [x] Cliquer sur un bouton de durée change la plage visible du
      graphique sans appel réseau supplémentaire.
- [x] Le bouton "Tout" revient à l'ensemble des données chargées
      (`fitContent`).
- [x] Changer d'actif ou de timeframe conserve la durée sélectionnée.
- [x] Le graphique affiche des données réelles dès le chargement de la
      page, sans action de l'utilisateur sur le bouton d'analyse.
- [x] Le bouton "Lancer l'analyse" est positionné sous le graphique (et
      sous la rangée de durées), plus jamais en recouvrement du
      graphique.
- [x] En mode plein écran, la rangée de durées et le bouton d'analyse
      sont masqués comme le reste de l'UI secondaire.
- [x] Les 117 tests backend passent (116 existants + 1 nouveau sur
      `_facts_pour_prompt`).

## Preuves de vérification

- `python -m pytest -q` → `117 passed`.
- Vérification visuelle via Playwright (serveur local, données réelles
  Binance) : positions relatives chart/durées/bouton mesurées par
  `getBoundingClientRect`, plage visible lue via
  `chart.timeScale().getVisibleRange()` avant/après clic sur "1M"
  (passe de `{from: 2025-04-25, to: 2026-10-24}` à
  `{from: 2026-09-24, to: 2026-10-24}`), visibilité des éléments en
  mode plein écran confirmée via `page.is_visible`.

## Journal

- **24/10/2026** — Les deux demandes sont arrivées coup sur coup pendant
  le développement et traitées ensemble car elles touchent la même zone
  de l'interface. `build_facts` passe à `candles_limit=1000` par défaut ;
  `_facts_pour_prompt` (nouveau, dans `app/llm/analysis.py`) retire les
  séries volumineuses du JSON envoyé au LLM sans toucher à la clé de
  cache ni au contrôle des chiffres, qui utilisent toujours le JSON
  complet. `definirPeriodeAffichee()` calcule les bornes de date à partir
  de la dernière bougie chargée (pas de la date système), pour rester
  cohérent même si les données sont légèrement en retard. Testé en
  conditions réelles (réseau Binance réel depuis ce sandbox) via
  Playwright ; un test manuel par le propriétaire sur mobile (Tailscale)
  reste à faire après fusion.
