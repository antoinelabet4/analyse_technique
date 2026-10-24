# Spec technique : récupération des données de marché (Binance + fallback Kraken)

Cahier associé : docs/cahiers-des-charges/P1-mvp-moteur-texte-graphique.md
Statut : validé le 23/10/2026 par le propriétaire (architecture déjà fixée
dans le brief d'origine : Binance en priorité, Kraken en secours, cache
SQLite ; "Continue" du 23/10/2026 vaut accord pour l'implémentation de ce
sous-périmètre déjà spécifié, pas une nouvelle décision de conception)

## Besoin

Obtenir, pour un actif donné (BTC, ETH, XRP, TAO, RENDER) et un timeframe
(1D ou 1W), une série de chandeliers réelle, avec repli automatique sur
une source secondaire en cas d'échec de la source principale, mise en
cache pour éviter les appels redondants, et affichage honnête de la
source effectivement utilisée.

## Données

- **Source principale** : Binance spot, endpoint public
  `https://data-api.binance.vision/api/v3/klines` (sans clé, limite de
  débit ~1200/min, vérifié accessible depuis ce réseau le 23/10/2026 pour
  les 5 actifs en 1D et 1W : `BTCUSDT`, `ETHUSDT`, `XRPUSDT`, `TAOUSDT`,
  `RENDERUSDT`).
- **Source de secours** : Kraken public, endpoint
  `https://api.kraken.com/0/public/OHLC` (sans clé, vérifié accessible le
  23/10/2026 pour les 5 actifs : paires `XBTUSD`, `ETHUSD`, `XRPUSD`,
  `TAOUSD`, `RENDERUSD`). Risque identifié précédemment (retrait MiCA de
  Binance en France, cahier P1) : Kraken doit être un vrai fallback
  opérationnel, pas seulement documenté — testé ici en conditions
  réelles, pas supposé.
- **Cache** : SQLite (`/app/data/cache.db`, volume persistant déjà réservé
  dans le Dockerfile depuis le P0), conforme à l'architecture de
  persistance fixée dans le brief d'origine. Une ligne par
  (actif, timeframe) contenant la dernière série récupérée avec succès.
  Dans ce module, le cache sert uniquement de filet de sécurité en cas
  d'échec des deux sources live (voir Garde-fous) ; l'optimisation "une
  analyse par actif et par bougie clôturée" du brief d'origine (éviter un
  appel réseau quand aucune bougie n'a clôturé depuis la dernière analyse)
  est de la responsabilité de la couche appelante (cache des analyses,
  pas encore spécifiée), pas de ce module bas niveau qui privilégie
  toujours une donnée fraîche quand une source répond.
- **Aucune donnée inventée** : si les deux sources échouent, la fonction
  lève une erreur explicite plutôt que de renvoyer un cache périmé
  présenté comme frais, ou des données vides silencieusement. L'appelant
  (API) traduit cette erreur en statut "source indisponible" affiché tel
  quel à l'utilisateur.

## Contrat d'API / de fonction

Module `app/data/market.py` :

- `ASSETS: dict[str, dict]` — mapping actif → symboles par source
  (`{"BTC": {"binance": "BTCUSDT", "kraken": "XBTUSD"}, ...}`).
- `fetch_binance_klines(symbol: str, interval: str, limit: int) -> list[Candle]`
  (`interval` : `"1d"` ou `"1w"`). Lève `SourceUnavailable` sur erreur
  réseau, HTTP non 200, ou réponse mal formée.
- `fetch_kraken_ohlc(pair: str, interval_minutes: int, limit: int) -> list[Candle]`
  (1440 pour 1D, 10080 pour 1W). Mêmes garanties d'erreur.
- `get_candles(asset: str, timeframe: str) -> CandlesResult` — tente
  Binance, puis Kraken si Binance échoue, met à jour le cache SQLite, et
  retourne `{candles: list[Candle], source: "binance" | "kraken", a_jour_le: datetime}`.
  Lève `SourceUnavailable` si les deux sources échouent **et** qu'aucun
  cache exploitable n'existe.
- Si les deux sources échouent mais qu'un cache existe : retourne le
  cache avec `source: "cache"` et un champ `perime: true`, jamais
  présenté comme une donnée fraîche.

`Candle` : `{time: str (ISO date), open: float, high: float, low: float, close: float, volume: float}`.

## Garde-fous

- Timeout explicite (5s) sur chaque appel HTTP, pour ne jamais bloquer
  indéfiniment sur une source qui ne répond pas.
- Aucune clé API, aucun compte exchange : uniquement les endpoints
  publics en lecture seule.
- La source effectivement utilisée (`binance` / `kraken` / `cache`) est
  toujours renvoyée avec les données, jamais implicite, pour que
  l'interface affiche honnêtement l'état des sources (brief d'origine).
- Le cache SQLite ne contient que des données de marché publiques,
  aucune donnée personnelle.

## Plan de test

- `test_market_cache.py` : écrire puis relire une série de chandeliers
  dans le cache SQLite (fichier temporaire), vérifier qu'un cache à jour
  est servi sans réappel réseau (mock des fonctions `fetch_*`).
- `test_market_fallback.py` : avec `fetch_binance_klines` mocké pour
  lever `SourceUnavailable`, vérifier que `get_candles` bascule sur
  Kraken et renvoie `source: "kraken"`.
- `test_market_cache_perime.py` : les deux sources mockées en échec, un
  cache existant est servi avec `perime: true`.
- `test_market_aucune_source.py` : les deux sources mockées en échec,
  aucun cache : `SourceUnavailable` est levée, pas de donnée inventée.
- Pas de test contre le réseau réel dans la suite automatisée (CI stable,
  pas dépendante de la disponibilité de Binance/Kraken) ; la vérification
  réseau réelle de ce document (23/10/2026) sert de preuve manuelle
  ponctuelle, pas de test reproductible en CI.
