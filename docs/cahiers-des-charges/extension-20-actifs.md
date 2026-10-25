# Extension de la liste des actifs disponibles au top 20

## Objectif

Demande explicite du propriétaire (25/10/2026) : allonger la liste des
cryptos disponibles aux 20 plus grosses par capitalisation (contre 5
jusqu'ici, choisies initialement par le propriétaire).

## Périmètre

- Inclus :
  - Les 20 plus grosses cryptos par capitalisation (CoinGecko, donnée
    réelle au 25/10/2026, pas devinée depuis une connaissance
    potentiellement obsolète), hors stablecoins (USDT, USDC, DAI, USDS,
    USDE, USD1) et jetons sans réelle pertinence pour une analyse
    technique indépendante (ex. jetons propres à une seule plateforme
    d'échange comme WBT/LEO, produits structurés comme FIGR_HELOC).
  - TAO et RENDER conservés en plus du top 20, sur confirmation explicite
    du propriétaire (`AskUserQuestion`, 25/10/2026) bien qu'ils ne soient
    plus dans le vrai top 20 à cette date (rang 37 et 79) : c'étaient ses
    choix initiaux. 22 actifs au total.
  - Chaque actif ajouté a une paire Binance **et** Kraken vérifiée en
    conditions réelles (appel direct à l'API OHLC des deux sources, pas
    seulement la liste déclarée des paires), condition requise par le
    mécanisme de repli existant (`get_candles`).
  - Correctif de précision numérique (voir journal) : la liste contient
    désormais des actifs à très faible valeur unitaire (ex. SHIB
    ~0,000005), ce qui a révélé deux bugs réels d'arrondi fixe.
- Non inclus :
  - Les contrats Binance Futures (funding rate, open interest) ne sont
    étendus qu'aux actifs déjà vérifiés précédemment (BTC, ETH, XRP, TAO,
    RENDER) : l'API Binance Futures est bloquée (451) depuis ce sandbox,
    impossible de vérifier en conditions réelles quels nouveaux actifs
    ont un contrat futures sans deviner. Les nouveaux actifs afficheront
    "Pas de contrat futures connu" jusqu'à vérification depuis un
    emplacement qui a accès à cette API (ex. le mini PC, France).
  - Le résumé quotidien Telegram (n8n) itère maintenant sur 22 actifs au
    lieu de 5, donc 21 appels `build_facts` au lieu de 4 (plus lourd,
    plus de requêtes réseau) : fonctionnellement correct mais plus coûteux
    en temps d'exécution du déclenchement quotidien, non optimisé dans ce
    lot.

## État d'avancement

**Fait — 25/10/2026.**

## Critères de validation

- [x] `/api/assets` renvoie exactement 22 actifs : les 20 plus grosses
      cryptos (hors stablecoins et jetons non pertinents) + TAO + RENDER.
- [x] Chaque actif ajouté charge des données réelles de bout en bout
      (`/api/analysis/{actif}/1d` renvoie des bougies réelles depuis
      Binance).
- [x] Les actifs à très faible valeur unitaire (ex. SHIB) affichent des
      prix, moyennes mobiles et MACD avec une précision décimale
      suffisante pour être lisibles (pas "0.00" ou "0.00000000").
- [x] Le contrôle anti-invention du texte LLM continue de fonctionner
      correctement pour ces actifs (ne collapse plus tout vers "0.0").

## Journal

- **25/10/2026** — Classement réel récupéré via l'API CoinGecko (jamais
  deviné depuis une connaissance générale, qui peut être dépassée).
  Chaque candidat vérifié en conditions réelles contre les APIs OHLC
  Binance et Kraken avant inclusion (pas seulement la présence
  déclarée de la paire). TAO et RENDER conservés en plus du top 20 sur
  confirmation explicite, malgré leur rang réel bien en dehors du top
  20 (37 et 79).

  **Deux bugs réels de précision numérique trouvés pendant la
  vérification**, les deux liés à des arrondis fixes jamais pensés pour
  des actifs à très faible valeur unitaire (ex. SHIB ~0,000005) :
  - `_nombre_ou_none` (`app/engine/facts.py`) arrondissait tout à 6
    décimales fixes : le MACD de SHIB (de l'ordre de 10⁻⁷) devenait
    0,0 dans le JSON "facts" lui-même, avant même d'atteindre le LLM
    ou l'affichage. Corrigé par un arrondi dépendant de l'ordre de
    grandeur (jusqu'à 12 décimales pour les très petits nombres,
    comportement inchangé pour les prix "normaux" ≥ 1).
  - `app/llm/facts_check.py` arrondissait les nombres extraits (des
    facts et du texte généré) à 2 décimales fixes avant comparaison, et
    le plancher de tolérance était une valeur absolue fixe (0,01) :
    pour un actif à 0,000005, ça aurait accepté n'importe quel petit
    chiffre inventé comme "assez proche de zéro", neutralisant le
    contrôle anti-invention pour ces actifs. Corrigé par un arrondi à
    l'extraction moins agressif (10 décimales, le filtrage "assez
    proche" restant géré par la tolérance) et un plancher de tolérance
    lui aussi dépendant de l'ordre de grandeur.

  Côté graphique, même catégorie de bug trouvée visuellement : la
  précision par défaut de Lightweight Charts (2 décimales) affichait
  "0.00" pour les prix, moyennes mobiles et MACD de SHIB. Corrigé en
  calculant dynamiquement la précision d'affichage à partir du prix
  actuel de l'actif chargé (`precisionPourPrix`/`formatDePrix` dans
  `static/app.js`), appliquée au graphique de prix, aux moyennes
  mobiles et au MACD ; `formatNombre` (résumé texte) reçoit le même
  correctif.

  Vérifié en conditions réelles : chargement de bout en bout pour
  plusieurs nouveaux actifs (SOL, DOGE, SHIB, HBAR), rendu visuel
  correct pour SHIB (prix/MM/MACD lisibles, plus de "0.00"), BTC non
  affecté par le changement (toujours 2 décimales). 139 tests backend
  passent (133 existants adaptés + 6 nouveaux sur les deux correctifs
  de précision).
