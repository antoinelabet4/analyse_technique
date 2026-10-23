# P1 — MVP : moteur déterministe + texte + graphique (5 actifs)

## Objectif

Afficher, pour BTC, ETH, XRP, TAO et RENDER, un graphique en chandeliers
annoté (niveaux, moyennes mobiles, Ichimoku, scénarios) avec en dessous un
texte explicatif en français simple, à partir de données réelles (Binance
en priorité, Kraken en secours) et d'un moteur de calcul entièrement
déterministe, sans aucun chiffre inventé.

## Périmètre

- Inclus : récupération des bougies 1D/1W (Binance, fallback Kraken),
  cache disque, indicateurs (MM 50/200j, EMA 200s, RSI 14, ATR 14,
  volume, **Ichimoku Kinko Hyo**), détection de pivots et regroupement en
  zones de support/résistance (y compris le nuage Ichimoku comme zone
  dynamique), détermination du régime de marché, scénarios haussier/
  baissier/range avec condition de clôture/cible/invalidation, force
  relative des alts vs BTC, texte explicatif généré par LLM à partir d'un
  JSON "facts" exclusivement, contrôle automatique qu'aucun chiffre du
  texte n'est absent de ce JSON.
- Non inclus : dérivés (funding, OI, options), macro (F&G, dominance,
  DXY, S&P), on-chain, authentification, PWA installable, déclenchement
  n8n. Ces points arrivent en P2/P3.

## État d'avancement

**En cours — 23/10/2026.** Moteur d'indicateurs/niveaux/régime/scénarios
codé et testé (voir journal). Restent à faire : récupération des données
réelles (Binance/Kraken), force relative alts vs BTC, texte explicatif
LLM avec contrôle automatique, wiring vers l'API et le graphique.

## Critères de validation

- [ ] Pour chacun des 5 actifs, en 1D et en 1W : les indicateurs
      (MM/EMA/RSI/ATR/Ichimoku) sont calculés et correspondent à un calcul
      de référence sur un jeu de données figé (test unitaire).
- [ ] Les niveaux affichés (pivots + nuage Ichimoku) sont les 2-3 supports
      et résistances les plus proches du prix courant, avec nombre de
      touches et éventuelle inversion de rôle.
- [ ] Chaque scénario affiché a une condition de clôture vérifiable, une
      cible (zone suivante) et un niveau d'invalidation, sans probabilité
      chiffrée inventée.
- [ ] Le texte explicatif ne contient aucun nombre absent du JSON "facts"
      (contrôle automatique testé avec un cas qui doit échouer sciemment).
- [ ] Si Binance échoue, la source bascule sur Kraken et l'interface
      affiche la source effectivement utilisée.

## Journal

- **23/10/2026** — Démarrage de la spec technique. Demande explicite du
  propriétaire d'intégrer l'Ichimoku Kinko Hyo, très utilisé dans la
  méthode de Vincent Ganne. Les réglages précis utilisés par Ganne ne
  sont pas une information publique vérifiable dont je dispose ; la spec
  part des réglages classiques (9/26/52/26) et ce point est marqué comme
  à confirmer avant validation définitive, pas comme un fait établi.
- **23/10/2026** — Spec validée ("Go"). `app/engine/indicators.py` codé :
  SMA/EMA/RSI/ATR, Ichimoku complet (nuage traité comme un niveau
  dynamique au même titre que les zones de pivots), détection de pivots
  et regroupement en zones avec tolérance ATR, inversion de rôle
  (heuristique documentée dans le docstring), régime de marché combinant
  MM/EMA longue et signaux Ichimoku sans score composite caché, scénarios
  haussier/baissier/range avec cible et invalidation (support/résistance
  ou Kijun selon le plus proche). 42 tests unitaires passent, données
  figées (déterministes), aucun appel réseau ni LLM dans ce module.
