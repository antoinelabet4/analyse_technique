# P2 — Dérivés et macro

## Objectif

Enrichir l'analyse avec le contexte dérivés (funding, open interest,
options BTC/ETH) et macro (Fear & Greed, dominance BTC, DXY, S&P 500),
conformément au brief d'origine. Comme pour le P1, aucun chiffre
inventé : une source indisponible ou non vérifiable s'affiche comme
telle plutôt que d'être simulée.

## Périmètre

- Inclus : funding rate et open interest (Binance Futures, à vérifier
  depuis la France), options BTC/ETH (Deribit, API publique officielle),
  Fear & Greed Index (alternative.me), dominance BTC (CoinGecko),
  DXY et S&P 500 (source à déterminer, aucune confirmée à ce jour).
- Non inclus : on-chain (SOPR, coût de production), lignes de tendance
  de cycle, déclenchement n8n. Ces points arrivent en P3.
- Pas de dépôt "bot BTC v2" à réutiliser (vérifié avec le propriétaire,
  24/10/2026 : n'existe pas / pas identifié) — modules macro construits
  depuis zéro pour ce projet.

## État d'avancement

**À faire — 24/10/2026.** Vérification des sources en cours avant
rédaction de la spec technique.

## Critères de validation

- [ ] Chaque source (funding/OI, options, F&G, dominance, DXY, S&P) est
      vérifiée en conditions réelles depuis ce réseau avant d'être codée.
- [ ] Toute source indisponible ou non vérifiable est explicitement
      marquée comme telle dans l'interface, jamais simulée.
- [ ] Spec technique validée par le propriétaire avant l'écriture du
      code (règle CLAUDE.md).

## Journal

- **24/10/2026** — Démarrage. Confirmé avec le propriétaire qu'aucun
  dépôt "bot BTC v2" n'est à réutiliser. Lancement de la vérification
  des sources de données (certaines avaient déjà été signalées comme
  risquées lors de la recherche du 23/10/2026 pour le P0 : Binance
  Futures depuis la France, DXY/S&P 500 sans source gratuite confirmée).
