# Spec technique : squelette FastAPI + page de test graphique

Cahier associé : docs/cahiers-des-charges/P0-squelette-acces-mobile.md
Statut : validé le 23/10/2026 par le propriétaire (demande directe "lance le code" après présentation du plan P0)

## Besoin

Un serveur FastAPI unique qui sert une page HTML statique embarquant
Lightweight Charts v5 (vendorisé, pas de CDN) et un endpoint de
supervision, déployable en conteneur sur Coolify, testable depuis un
téléphone via Tailscale.

## Données

Aucune donnée réelle en P0. La page de test consomme un jeu de chandeliers
factice généré côté serveur (`app/fixtures.py`), explicitement labellisé
comme donnée de démonstration dans l'interface (bandeau visible), jamais
présenté comme une donnée de marché réelle — conforme au principe "aucune
donnée inventée" : ici ce n'est pas une donnée de marché inventée, c'est
un jeu de test explicitement annoncé comme tel.

## Contrat d'API / de fonction

- `GET /health` → `200 {"status": "ok"}`. Pas d'authentification (lecture
  de supervision uniquement, aucune donnée sensible).
- `GET /` → page HTML statique (`static/index.html`), avec les assets
  (`static/vendor/lightweight-charts.standalone.production.js`,
  `static/app.js`, `static/style.css`) servis par FastAPI
  (`StaticFiles`).
- `GET /api/test-candles` → `200 [{time, open, high, low, close}, ...]`,
  données figées générées par `app/fixtures.py`, aucun cas d'erreur
  (fonction pure, pas d'E/S).

## Garde-fous

- Pas de clé ni de secret nécessaire en P0 ; `.env.example` documente
  uniquement les variables prévues pour les phases suivantes
  (`ANTHROPIC_API_KEY`, `LLM_MODEL`), non utilisées par ce code.
- Le conteneur tourne avec un utilisateur non root, limites mémoire/CPU
  documentées dans le README, healthcheck sur `/health`.
- Aucun appel réseau sortant au runtime : le JS du graphique est
  vendorisé, pas chargé depuis un CDN, pour fonctionner en réseau privé
  derrière Tailscale.

## Plan de test

- `tests/test_health.py` : `GET /health` retourne 200 et le JSON attendu.
- `tests/test_fixtures.py` : `app/fixtures.py` retourne une série de
  chandeliers cohérente (high ≥ max(open, close), low ≤ min(open, close),
  dates croissantes), avec un jeu de données figé en entrée du test.
- Recette manuelle (documentée dans la PR, pas automatisable en P0) :
  ouvrir la page depuis un téléphone connecté au tailnet, vérifier
  l'affichage plein écran et les gestes tactiles (pan/zoom).
