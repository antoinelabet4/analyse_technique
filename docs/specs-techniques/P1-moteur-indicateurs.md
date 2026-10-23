# Spec technique : moteur d'indicateurs (MM/EMA/RSI/ATR/Ichimoku) et niveaux

Cahier associé : docs/cahiers-des-charges/P1-mvp-moteur-texte-graphique.md
Statut : brouillon

## Besoin

Calculer, pour une série de bougies (1D ou 1W) d'un actif donné, l'ensemble
des indicateurs et niveaux nécessaires à l'affichage et au texte
explicatif, de façon entièrement déterministe (aucun appel LLM dans ce
module). L'Ichimoku Kinko Hyo est intégré comme composant à part entière,
au même titre que les moyennes mobiles, car c'est un outil central de la
méthode de Vincent Ganne dont s'inspire ce projet.

**Point à trancher avant validation** : les réglages Ichimoku ci-dessous
(9/26/52/26) sont les réglages classiques de la méthode japonaise
d'origine. Je n'ai pas de source vérifiable sur un éventuel paramétrage
différent utilisé spécifiquement par Vincent Ganne. Si vous avez cette
information (vidéo, document), elle prime sur les valeurs par défaut
ci-dessous ; sinon on démarre avec les réglages classiques, clairement
documentés comme tels dans l'interface (pas présentés comme "la méthode
Ganne exacte").

## Données

Entrée : une liste de chandeliers `{time, open, high, low, close, volume}`,
déjà récupérée et mise en cache par le module de données (hors périmètre
de cette spec). Aucune donnée n'est générée ou extrapolée par ce module :
si l'historique est insuffisant pour un indicateur (ex. moins de 52
bougies pour Senkou Span B), cet indicateur est explicitement marqué
`insuffisant` dans le JSON de sortie plutôt que calculé partiellement ou
omis silencieusement.

## Contrat d'API / de fonction

Module `app/engine/indicators.py`, fonctions pures (pandas/numpy), aucun
I/O.

### Moyennes mobiles et volatilité

- `sma(closes: pd.Series, period: int) -> pd.Series`
- `ema(closes: pd.Series, period: int) -> pd.Series`
- `rsi(closes: pd.Series, period: int = 14) -> pd.Series` (formule de
  Wilder, lissage exponentiel)
- `atr(candles: pd.DataFrame, period: int = 14) -> pd.Series` (true range
  de Wilder)

Utilisés avec : MM 50 et MM 200 (clôtures, 1D), EMA 200 (clôtures, 1W),
RSI 14, ATR 14 — conformes au brief d'origine.

### Ichimoku Kinko Hyo

`ichimoku(candles: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52, shift: int = 26) -> IchimokuResult`

Calcule, sur les `high`/`low`/`close` de la série :

- **Tenkan-sen** (ligne de conversion) : `(max(high, tenkan) + min(low, tenkan)) / 2`
- **Kijun-sen** (ligne de base) : `(max(high, kijun) + min(low, kijun)) / 2`
- **Senkou Span A** : `(tenkan + kijun) / 2`, décalée de `shift` périodes
  vers l'avant (projection du nuage dans le futur)
- **Senkou Span B** : `(max(high, senkou_b) + min(low, senkou_b)) / 2`,
  décalée de `shift` périodes vers l'avant
- **Chikou Span** : `close` décalée de `shift` périodes vers l'arrière
- **Nuage (kumo)** : zone entre Senkou A et Senkou B à une date donnée ;
  couleur haussière si Senkou A > Senkou B, baissière sinon

Retourne un objet avec les 5 séries plus, pour la dernière bougie
clôturée : `prix_vs_nuage` (`au_dessus` / `dans` / `en_dessous`),
`couleur_nuage` (`haussier` / `baissier`), `tenkan_vs_kijun`
(`croisement_haussier` / `croisement_baissier` / `aucun`, détecté sur les
2 dernières bougies), et `chikou_vs_prix_historique` (`au_dessus` /
`en_dessous` / `indisponible` si l'historique ne couvre pas `shift`
périodes avant le point de départ de la série).

### Niveaux (pivots + nuage)

`levels(candles: pd.DataFrame, atr: pd.Series, ichimoku: IchimokuResult) -> list[Level]`

- Détection des pivots (swing highs/lows, fenêtre configurable) déjà
  prévue au brief d'origine, regroupement en zones par tolérance en ATR,
  comptage des touches, détection d'inversion de rôle (ancien support
  devenu résistance), ancien record historique.
- Ajout : les bornes actuelles du nuage Ichimoku (Senkou A et B à la
  bougie courante) sont ajoutées comme niveau dynamique de type `nuage`,
  avec la même structure que les autres niveaux (`prix_haut`,
  `prix_bas`, `type: "nuage"`), pour que le graphique et le texte les
  traitent de façon uniforme avec les zones de pivots.
- Garder uniquement les 2-3 supports et 2-3 résistances les plus proches
  du prix courant, tous types de niveaux confondus (pivot ou nuage),
  triés par proximité.

### Régime de marché

`regime(candles, sma50, sma200, ema200w, ichimoku) -> Regime`

Combine, sans pondération inventée (chaque signal est rapporté tel quel,
pas agrégé en un score composite non justifié) :

- position du prix vs MM200 (1D) / EMA200 (1W), pente de ces moyennes ;
- structure des sommets/creux (suite haussière, baissière, ou range) ;
- position du prix vs nuage Ichimoku, couleur du nuage, et l'éventuel
  croisement Tenkan/Kijun récent, rapportés comme signaux Ichimoku
  distincts (pas fondus dans un seul "régime global" qui masquerait un
  désaccord entre MM et Ichimoku, ce désaccord étant lui-même une
  information utile à afficher).

### Scénarios

`scenarios(regime, levels, ichimoku) -> list[Scenario]`

Haussier / baissier / range, chacun avec :

- condition de clôture (journalière ou hebdo) déclenchant le scénario ;
- cible = prochaine zone de niveau (pivot ou nuage) ;
- invalidation = niveau opposé le plus proche ; pour un scénario haussier
  qui s'appuie sur l'Ichimoku, l'invalidation peut être la base du nuage
  (Senkou B) ou le Kijun-sen selon lequel est le plus proche du prix,
  nommé explicitement dans le scénario (pas une valeur générique).

Pas de probabilité chiffrée inventée, conforme au brief d'origine.

## Garde-fous

- Toute fonction est pure (pas d'accès réseau, pas d'horloge système
  implicite) pour rester testable avec des données figées.
- Un indicateur dont l'historique est insuffisant est marqué comme tel
  dans la sortie, jamais calculé sur une fenêtre tronquée silencieuse.
- Aucun score composite caché : chaque signal (MM, Ichimoku, structure de
  prix) reste individuellement traçable dans le JSON "facts", pour que le
  texte explicatif (LLM) puisse citer la source de chaque affirmation.
- Le paramétrage Ichimoku (9/26/52/26 par défaut) est une constante
  nommée et documentée, pas une valeur en dur dispersée dans le code,
  pour pouvoir l'ajuster facilement si vous confirmez un réglage
  spécifique à la méthode Ganne.

## Plan de test

Jeu de données figé par actif (`tests/fixtures/<actif>_1d.json`,
`<actif>_1w.json`), au moins 60 bougies 1D et 60 bougies 1W par actif pour
couvrir Senkou Span B (52 périodes) :

- `test_indicators_sma_ema.py` : SMA/EMA comparées à un calcul de
  référence (ex. pandas `.rolling().mean()` sur le même jeu, ou valeurs
  calculées à la main sur un petit échantillon).
- `test_indicators_rsi_atr.py` : RSI et ATR sur un cas connu (ex. série
  monotone croissante → RSI proche de 100 ; série plate → ATR proche de
  0).
- `test_ichimoku.py` : les 5 lignes Ichimoku sur un jeu figé, y compris le
  cas `chikou_vs_prix_historique == "indisponible"` quand la série est
  trop courte, et le cas `prix_vs_nuage` dans les 3 états possibles sur 3
  échantillons différents.
- `test_levels.py` : zones de pivots regroupées correctement (tolérance
  ATR), inversion de rôle détectée sur un cas construit exprès, nuage
  Ichimoku bien ajouté comme niveau de type `nuage`.
- `test_scenarios.py` : chaque scénario généré a une cible et une
  invalidation qui correspondent à un niveau réellement présent dans la
  liste de niveaux (pas une valeur orpheline).
