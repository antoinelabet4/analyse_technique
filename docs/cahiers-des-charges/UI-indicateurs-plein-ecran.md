# UI — Sélection des indicateurs + graphique plein écran

## Objectif

Deux demandes explicites du propriétaire pendant le développement du P3 :
pouvoir choisir quels indicateurs afficher sur le graphique (menu
déroulant), et agrandir le graphique en plein écran (notamment en
orientation paysage) pour mieux le lire.

## Périmètre

- Inclus : menu "Indicateurs" (moyennes mobiles, nuage Ichimoku,
  niveaux, zones opportunité/risque), état mémorisé dans le navigateur
  (localStorage, par appareil) ; bouton "Agrandir" qui fait passer le
  graphique en plein écran (mode CSS qui fonctionne partout, tentative
  best-effort de l'API Fullscreen native en plus) ; le graphique profite
  aussi automatiquement de plus de hauteur si le téléphone est tourné en
  paysage, plein écran ou non.
- Non inclus : verrouillage de l'orientation de l'écran (API non
  supportée par Safari iOS, cas d'usage principal du propriétaire) —
  l'utilisateur tourne son téléphone manuellement, le graphique
  s'adapte.

## État d'avancement

**Fait — 24/10/2026.**

## Critères de validation

- [x] Décocher un indicateur le masque immédiatement sans recharger les
      données (pas de nouvel appel réseau).
- [x] La préférence survit à un changement d'actif/timeframe et à un
      rechargement de page (localStorage).
- [x] Le bouton "Agrandir" fait passer le graphique en plein écran,
      masque le reste de l'interface, un bouton de fermeture visible
      permet de revenir en arrière.
- [x] En orientation paysage (téléphone tourné), le graphique utilise
      davantage de hauteur même sans activer le plein écran.

## Journal

- **24/10/2026** — Implémenté en même temps que la fin du P3, sur
  demande explicite pendant le développement. Le plein écran utilise un
  mode CSS maison (position fixed, reste de l'UI masqué) plutôt que de
  dépendre uniquement de l'API Fullscreen du navigateur : celle-ci n'est
  pas fiable sur Safari iOS pour un élément autre qu'une vidéo, elle
  reste tentée en complément (fonctionne sur Chrome/Android) mais le
  mode CSS est le comportement garanti. Vérifié dans un vrai navigateur :
  masquage/affichage des indicateurs, plein écran et retour, rendu en
  viewport paysage. 116 tests backend toujours verts (aucun changement
  backend sur ce lot).
- **24/10/2026 (correctif)** — Les moyennes mobiles (MM50/MM200/EMA200)
  étaient affichées comme une ligne de prix fixe (valeur actuelle
  uniquement), pas comme une vraie courbe suivant le prix dans le temps.
  Demande explicite du propriétaire : `build_facts` calcule et renvoie
  maintenant la série complète (`moyennes_mobiles_serie`), tracée côté
  client en `LightweightCharts.LineSeries` (une par moyenne mobile),
  recréée à chaque rechargement de données comme les lignes de prix des
  niveaux (même correctif d'ordre que le bug d'échelle du 24/10/2026 :
  les anciennes courbes sont retirées avant le `setData()` du nouvel
  actif, jamais après). Vérifié visuellement (courbes bleue/orange
  suivant le prix sur BTC, masquage via la case à cocher, changement
  d'actif BTC→ETH sans courbe résiduelle ni erreur JS) et par test
  (`tests/test_api_analysis.py`, `tests/llm/test_analysis.py` pour
  confirmer que la série n'est pas envoyée au LLM). 117 tests backend
  toujours verts.
