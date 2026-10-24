# P3 — On-chain, lignes de tendance de cycle, déclenchement n8n

## Objectif

Dernière phase du brief d'origine : indicateurs on-chain (si une source
fiable existe), lignes de tendance de cycle, et déclenchement d'une
analyse quotidienne par le n8n existant du propriétaire, avec envoi
d'un résumé (Telegram ou e-mail).

## Périmètre

- Inclus (sous réserve des clarifications ci-dessous) : SOPR, MVRV,
  MVRV Z-score, Puell Multiple (source `bitcoin-data.com`, vérifiée
  accessible le 24/10/2026, communautaire et gratuite, sans clé) ;
  lignes de tendance de cycle (définition à clarifier avec le
  propriétaire, voir journal) ; endpoint protégé déclenchable par n8n,
  envoi du résumé par Telegram ou e-mail (canal et identifiants à
  fournir par le propriétaire).
- Non inclus : "coût de production" tel que décrit dans le brief
  d'origine — aucune source gratuite fiable trouvée qui le calcule
  directement ; le calculer nous-mêmes exigerait une hypothèse de prix
  de l'électricité et d'efficacité des machines de minage, ce qui en
  ferait une estimation, pas un fait, contrairement à la règle du
  projet. Point soumis au propriétaire (voir questions).

## État d'avancement

**Fait pour la portée retenue — 24/10/2026.** On-chain, canal de cycle
et déclenchement n8n codés et testés (voir journal).

## Critères de validation

- [ ] Chaque métrique on-chain affichée a une source identifiée et un
      indicateur de fraîcheur (ces sources ont un délai, pas du temps
      réel).
- [ ] Aucune métrique n'est présentée comme un fait si elle repose sur
      une hypothèse (ex. coût de production, si retenu malgré tout).
- [ ] Spec technique validée par le propriétaire avant code.

## Journal

- **24/10/2026** — Recherche de sources on-chain. `bitcoin-data.com`
  (communautaire, gratuit, sans clé) confirmé accessible avec SOPR,
  MVRV, MVRV Z-score, realized price/cap, Puell Multiple, NUPL,
  active addresses. Pas de "coût de production" direct. Décalage
  observé sur le SOPR : dernière donnée à J-7 environ (pas temps réel),
  à surveiller. Source communautaire non officielle : pas de garantie
  de pérennité, à documenter comme tel dans l'interface si retenue.
- **24/10/2026** — Décisions validées par le propriétaire : coût de
  production abandonné (pas de source fiable, aurait exigé une
  hypothèse) ; "lignes de tendance de cycle" = canal de régression
  log-linéaire sur l'historique BTC déjà récupéré ; déclenchement n8n
  via Telegram (bot déjà existant côté propriétaire).
- **24/10/2026** — Code livré : `app/data/onchain.py` (SOPR, MVRV,
  MVRV Z-score, Puell Multiple, cache 6h), `app/engine/cycle.py`
  (régression log-linéaire + cache 6h sur 1000 bougies hebdo BTC),
  `app/notifications/telegram.py`, `app/engine/daily_summary.py`,
  `POST /api/daily-trigger` protégé par `X-Trigger-Token` (comparaison
  à temps constant). Variables d'environnement ajoutées à
  `.env.example` (`N8N_TRIGGER_TOKEN`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`), jamais de vraie valeur commise. Vérifié en
  conditions réelles : on-chain et cycle alimentent bien
  `/api/analysis/BTC/1d`, `/api/daily-trigger` refuse sans le bon
  token. Envoi Telegram réel non testé (pas de bot configuré dans ce
  sandbox) : à faire une fois les variables renseignées sur le mini
  PC. 116 tests passent.
