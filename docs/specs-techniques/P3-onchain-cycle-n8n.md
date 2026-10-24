# Spec technique : on-chain, canal de régression de cycle, déclenchement n8n

Cahier associé : docs/cahiers-des-charges/P3-onchain-cycle-n8n.md
Statut : validé le 24/10/2026 par le propriétaire (coût de production abandonné ; canal de régression log-linéaire pour les "lignes de tendance" ; Telegram pour le déclenchement n8n)

## Besoin

1. Afficher des métriques on-chain BTC réelles (SOPR, MVRV, MVRV
   Z-score, Puell Multiple) en contexte, avec repli honnête si la
   source échoue.
2. Afficher un canal de régression logarithmique sur l'historique des
   prix BTC (tendance de cycle), calculé à partir des données déjà
   récupérées, pas une nouvelle source.
3. Un endpoint protégé, déclenchable par le n8n du propriétaire, qui
   produit une analyse quotidienne et l'envoie sur Telegram.

## Données

- **On-chain** : `bitcoin-data.com/v1/{metrique}` (communautaire,
  gratuit, sans clé, vérifié le 24/10/2026). Métriques retenues :
  `sopr`, `mvrv`, `mvrv-zscore`, `puell-multiple`. **Source non
  officielle, pas de garantie de pérennité** : affichée comme telle
  dans l'interface. Décalage observé d'environ une semaine sur le
  SOPR (pas temps réel) : la date de la donnée est toujours affichée,
  jamais seulement sa valeur.
- **Canal de cycle** : calculé depuis les bougies BTC hebdomadaires déjà
  disponibles via `app/data/market.py` (étendu avec un plus grand
  historique, jusqu'à 1000 bougies hebdo, soit l'historique Binance
  complet pour BTCUSDT depuis son listing ~2017 — **pas l'historique
  complet de Bitcoin depuis 2009**, limite explicitement documentée).
  Régression `ln(close) = a + b·t`, canal = régression ± écart-type des
  résidus. Donnée dérivée, pas une prédiction : présentée comme telle.
- **Déclenchement n8n** : `POST /api/daily-trigger`, protégé par un
  en-tête `X-Trigger-Token` comparé à la variable d'environnement
  `N8N_TRIGGER_TOKEN` (comparaison à temps constant). Construit un
  résumé quotidien (BTC en détail : régime, scénarios, on-chain,
  position dans le canal de cycle ; un résumé court par alt : prix,
  force relative) et l'envoie via l'API Telegram Bot
  (`https://api.telegram.org/bot<TOKEN>/sendMessage`) au `chat_id`
  configuré. Jeton du bot et chat_id dans `TELEGRAM_BOT_TOKEN` /
  `TELEGRAM_CHAT_ID`, jamais dans le code ni commités — à renseigner
  directement dans les variables d'environnement Coolify, jamais collés
  dans une conversation.

## Contrat d'API / de fonction

- `app/data/onchain.py` : `get_onchain_metrics() -> OnchainMetrics`
  (un seul appel groupé pour les 4 métriques BTC, cache TTL 6h, motif
  `disponible`/`raison` déjà utilisé par `derivatives.py`/`macro.py`).
- `app/engine/cycle.py` : `regression_log_lineaire(candles: pd.DataFrame) -> CanalCycle`
  (fonction pure), retourne la valeur actuelle de la tendance centrale
  et des deux bornes du canal, plus la position du prix actuel dans ce
  canal (`"au_dessus"`/`"dans"`/`"en_dessous"`).
- `app/data/market.py` : `get_candles` déjà paramétrable en `limit` —
  réutilisé avec `limit=1000` pour ce besoin spécifique, pas de
  nouvelle fonction de récupération.
- `POST /api/daily-trigger` : 401 si l'en-tête est absent ou incorrect,
  200 avec un résumé de ce qui a été envoyé (pas le contenu complet, un
  accusé de réception) si l'envoi Telegram réussit, 502 si Telegram
  échoue (avec le détail technique en log serveur seulement, jamais
  dans la réponse).

## Garde-fous

- `N8N_TRIGGER_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  uniquement en variables d'environnement, ajoutées à `.env.example`
  avec des valeurs d'exemple vides, jamais de vraie valeur dans le
  dépôt ni dans une conversation.
- Comparaison du token à temps constant (`hmac.compare_digest`) pour
  éviter une attaque par timing, même si le risque est faible pour un
  usage perso.
- Le canal de cycle est explicitement étiqueté comme une donnée
  dérivée/statistique, jamais comme une prédiction de prix (conforme à
  l'interdiction du brief).
- Toute métrique on-chain indisponible (source en panne) ne bloque pas
  l'envoi du résumé Telegram : elle est omise avec une mention
  explicite "indisponible aujourd'hui", jamais une valeur inventée.

## Plan de test

- `test_onchain.py` : mock des réponses `bitcoin-data.com`, cas succès
  et échec, cache TTL vérifié.
- `test_cycle.py` : régression log-linéaire sur une série figée de prix
  croissant exponentiellement (cas construit où la réponse attendue est
  calculable à la main), position dans le canal testée dans ses 3 états.
- `test_daily_trigger.py` : 401 sans token ou avec un mauvais token,
  200 avec le bon token (appel Telegram mocké), 502 si l'appel Telegram
  mocké échoue.
- Aucun test contre le réseau réel (on-chain, Telegram) dans la suite
  automatisée.
