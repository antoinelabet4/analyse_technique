# Spec technique : dérivés (funding, OI, options) et macro (F&G, dominance, DXY, S&P)

Cahier associé : docs/cahiers-des-charges/P2-derives-macro.md
Statut : validé le 24/10/2026 par le propriétaire (croisement Yahoo/FRED pour le S&P 500 ; DXY sans vraie seconde source, FRED DTWEXBGS affiché en contexte complémentaire clairement distinct, pas comme un croisement du même chiffre)

## Besoin

Ajouter au JSON "facts" un bloc "dérivés" (funding rate, open interest,
contexte options pour BTC/ETH) et un bloc "macro" (Fear & Greed,
dominance BTC, DXY, S&P 500), affichés comme contexte sous le graphique,
sans jamais inventer de valeur si une source est indisponible.

## Point important : vérification faite depuis une IP américaine, pas française

Les vérifications réseau de cette spec ont été faites depuis le sandbox
cloud de cette session, dont l'IP sortante est localisée aux États-Unis
(confirmé via ifconfig.co). Binance Futures (451) et Bybit (403)
signalent tous deux un blocage géographique — **probablement lié aux
restrictions US sur ces plateformes, pas nécessairement à la France**.
Je ne peux pas conclure à la place du propriétaire sur ce que verra le
mini PC (IP française). Le code est donc conçu pour tolérer un échec de
ces sources sans aucune hypothèse sur leur disponibilité réelle, et le
propriétaire est invité à vérifier directement depuis le mini PC :

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
```

200 = accessible, 451 = bloqué même depuis la France.

## Données

- **Funding rate + Open Interest** : `fapi.binance.com` (Binance
  Futures, public, sans clé). `/fapi/v1/premiumIndex` (funding actuel),
  `/fapi/v1/openInterest` (OI actuel). Si indisponible (451 ou autre
  échec), le bloc "dérivés" affiche `"disponible": false` avec la
  raison, jamais une valeur substituée.
- **Options BTC/ETH** : `deribit.com/api/v2/public/get_book_summary_by_currency`
  (vérifié accessible le 24/10/2026, public, sans clé). Retenir un
  résumé simple : put/call ratio approximatif (ratio du nombre
  d'instruments ou de l'open interest put vs call), pas de grecques
  (hors périmètre).
- **Fear & Greed** : `api.alternative.me/fng/?limit=1` (vérifié
  accessible, public, sans clé, pas de limite connue).
- **Dominance BTC** : `api.coingecko.com/api/v3/global`, champ
  `market_cap_percentage.btc`. Vérifié accessible mais **rate-limit
  partagé agressif** (429 rencontré une fois sur deux appels
  rapprochés) : mise en cache obligatoire, pas d'appel direct à chaque
  requête utilisateur (réutilise le pattern du cache de marché du P1,
  TTL raisonnable ex. 15 min, pas de donnée inventée en cas d'échec,
  juste `"disponible": false`).
- **DXY et S&P 500** : `query1.finance.yahoo.com/v8/finance/chart/{symbole}`
  avec en-tête `User-Agent` obligatoire (sans lui, 429 systématique dans
  nos tests). Symboles : `DX-Y.NYB` (DXY), `%5EGSPC` (S&P 500). **API
  non officielle, non documentée, peut changer ou se fermer sans
  préavis** : à surveiller, prévoir un message clair si elle cesse de
  répondre plutôt qu'un plantage silencieux. Stooq testé et rejeté
  (connexion TLS réinitialisée systématiquement, inutilisable).
- **Croisement validé le 24/10/2026** : `fred.stlouisfed.org/graph/fredgraph.csv?id=SP500`
  (Federal Reserve, officiel, sans clé, vérifié accessible) sert de
  second avis pour le S&P 500 — écart anormal entre Yahoo et FRED
  (> 2%, seuil arbitraire documenté comme tel) signalé explicitement
  dans l'interface plutôt que masqué. Pour le DXY, pas de vraie
  équivalence officielle gratuite : `id=DTWEXBGS` (indice dollar
  pondéré du commerce, Fed, panier et méthodologie différents de l'ICE
  DXY) est affiché à part, explicitement étiqueté comme un indicateur
  complémentaire et non un croisement du même chiffre.

## Contrat d'API / de fonction

- `app/data/derivatives.py` : `get_funding_oi(asset: str) -> FundingOI`,
  `get_options_context(asset: str) -> OptionsContext`. Chaque résultat a
  un champ `disponible: bool` et `raison: str | None`.
- `app/data/macro.py` : `get_fear_greed() -> FearGreed`,
  `get_btc_dominance() -> Dominance` (cache SQLite 15 min),
  `get_dxy() -> IndiceMacro`, `get_sp500() -> IndiceMacro`. Même
  contrat `disponible`/`raison`.
- `build_facts` (P1, `app/engine/facts.py`) étendu avec deux blocs
  optionnels `"derives"` et `"macro"`, chacun indiquant pour chaque
  sous-source si elle est disponible.
- Nouvel appel groupé côté frontend (ou extension de l'existant) pour
  afficher ce contexte sous le graphique, dans une section repliable
  "Contexte macro et dérivés", avec un badge par source
  (disponible/indisponible).

## Garde-fous

- Timeout explicite (5s) par source, chaque source interrogée
  indépendamment : l'échec d'une source n'empêche jamais l'affichage
  des autres.
- Aucune donnée simulée ou approximée présentée comme réelle. Un badge
  "indisponible" par source plutôt qu'un silence ou une estimation.
- Dépendance à une API non documentée (Yahoo Finance) explicitement
  signalée dans l'interface (ex. tooltip "source non officielle") pour
  que le propriétaire ne soit jamais surpris si elle cesse de
  fonctionner.

## Plan de test

- `test_derivatives.py` : mock des réponses Binance Futures (succès,
  451, timeout) → `disponible` correctement renseigné dans chaque cas.
- `test_macro.py` : mock des 4 sources, cache de la dominance BTC
  vérifié (pas de second appel réseau avant expiration du TTL), erreur
  Yahoo Finance gérée proprement.
- Pas de test contre le réseau réel dans la suite automatisée (comme
  pour le P1) ; la vérification de cette spec (24/10/2026, depuis une
  IP US) sert de preuve ponctuelle, à reconfirmer depuis le mini PC pour
  les sources dérivés.
