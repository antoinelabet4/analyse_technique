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

**En cours — 24/10/2026.** Moteur d'indicateurs/niveaux/régime/scénarios,
récupération de données réelles (Binance + fallback Kraken + cache
SQLite), force relative vs BTC, et câblage API + graphique mobile codés,
testés et vérifiés dans un vrai navigateur (voir journal). Reste à
faire : texte explicatif LLM avec contrôle automatique.

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
- **23/10/2026** — `app/data/market.py` codé : Binance (endpoint public
  `data-api.binance.vision`) en priorité, Kraken en secours, cache SQLite
  comme filet de sécurité si les deux échouent (jamais présenté comme une
  donnée fraîche : champ `perime: true`). Accessibilité vérifiée en
  conditions réelles depuis ce réseau pour les 5 actifs (BTC, ETH, XRP,
  TAO, RENDER) sur les deux sources, en 1D et en 1W. 52 tests passent
  (10 nouveaux : bascule de source, cache périmé, aucune source + aucun
  cache, parsing contre des réponses réellement capturées le 23/10/2026).
  Pipeline vérifié de bout en bout avec un appel réseau réel (hors suite
  automatisée). Note : l'optimisation "pas de rappel réseau si aucune
  bougie n'a clôturé" du brief d'origine est reportée à la couche de
  cache des analyses (pas encore spécifiée), ce module privilégiant
  toujours une donnée fraîche quand une source répond (voir spec).
- **24/10/2026** — Force relative vs BTC (`app/engine/relative_strength.py`,
  ratio actif/BTC sur 30 bougies), assemblage du JSON "facts"
  (`app/engine/facts.py`) et endpoints API (`/api/assets`,
  `/api/analysis/{actif}/{timeframe}`) codés. Interface mobile mise à
  jour : sélecteur d'actif, bascule 1D/1W, chandeliers réels, niveaux de
  prix (MM/EMA, nuage, supports/résistances) en overlay, résumé en
  sections repliables à partir des chiffres bruts (pas de texte LLM
  encore). Vérifié dans un vrai navigateur (Chromium headless, viewport
  mobile 390×844) : capture d'écran BTC/1D et ETH/1W conformes.
  **Bug trouvé et corrigé pendant cette vérification** : un clic rapide
  sur un actif puis un timeframe lançait deux requêtes concurrentes ; si
  la première répondait après la seconde, elle écrasait l'affichage avec
  des données périmées (ETH affiché avec les MM 1D au lieu de l'EMA200
  1W). Corrigé par un identifiant de requête qui ignore toute réponse
  devenue obsolète. 63 tests passent.
- **24/10/2026** — Itération interface suite au premier test réel sur le
  mini PC (déploiement Coolify + accès Tailscale confirmés fonctionnels) :
  - Ce qui semblait être un bug d'échelle qui ne se mettait pas à jour
    entre actifs était en fait l'absence d'indicateur de chargement
    pendant l'appel réseau réel à Binance (quelques secondes) : ajout
    d'un état de chargement visible (graphique assombri, badge "Chargement
    de X…").
  - Nuage Ichimoku et niveaux affichés comme de vraies bandes colorées
    remplies (overlay positionné via `priceToCoordinate`, resynchronisé au
    zoom/pan et au redimensionnement), plus seulement des lignes
    horizontales.
  - Ajout de **zones d'opportunité et de risque** sur le graphique,
    demandées par le propriétaire. Point de vigilance soulevé par l'agent
    avant implémentation : le brief interdit tout "conseil d'achat ou de
    vente". Le propriétaire a tranché le 24/10/2026 : reformulation sans
    ces mots ("Zone d'opportunité" / "Zone de risque"), dérivées des
    cibles déjà calculées par les scénarios haussier/baissier existants
    (mêmes chiffres que la section Scénarios, aucune donnée nouvelle
    inventée).
  - Sélecteur d'actif remplacé par un menu déroulant (anticipe l'ajout de
    tous les actifs disponibles sur TradingView, hors périmètre pour
    l'instant).
  - Toute mention de Vincent Ganne retirée de l'interface (sur demande
    explicite), disclaimer reformulé : "Analyse technique automatisée,
    générée automatiquement. Ce n'est pas un conseil financier."
  - Passe de design pour un rendu plus "app" (en-tête collant, cartes
    arrondies, select natif stylé, transitions douces).
  - Vérifié dans un vrai navigateur (chargement, bascule d'actif avec
    zoom/pan, positionnement des bandes). 63 tests toujours verts (aucun
    changement backend).
