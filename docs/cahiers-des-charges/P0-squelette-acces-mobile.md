# P0 — Squelette Docker + accès mobile

## Objectif

Disposer d'un squelette d'application déployable sur Coolify, avec une
page de test affichant un graphique en chandeliers (données figées) via
TradingView Lightweight Charts v5, accessible depuis un téléphone en
HTTPS avant de construire le moteur d'analyse réel. Valider l'accès
mobile avant tout le reste, comme demandé dans le brief du projet.

## Périmètre

- Inclus : application FastAPI minimale (`/health`, page statique unique),
  Lightweight Charts v5 vendorisé (pas de CDN au runtime), page de test en
  mode sombre par défaut, pensée mobile d'abord (plein écran, tactile),
  Dockerfile léger avec healthcheck, `.env.example`, README avec étapes de
  déploiement Coolify et guide Tailscale.
- Non inclus : récupération de données réelles (Binance/Kraken), moteur
  d'indicateurs et de niveaux, texte explicatif LLM, PWA installable
  (manifest/icônes), authentification, cache SQLite. Ces points arrivent
  en P1 ou plus tard.

## État d'avancement

**En cours — 23/10/2026** (code et tests livrés ; build Docker et accès
Tailscale réel restent à vérifier par le propriétaire, voir journal).

## Critères de validation

- [x] `GET /health` répond 200 avec un statut JSON (vérifié : test
      automatisé + appel réel en local).
- [x] `GET /` affiche un graphique en chandeliers sur des données figées,
      en plein écran mobile, sans appel réseau externe au runtime (le JS
      du graphique est servi depuis ce serveur, vérifié par appel direct
      sur `/static/vendor/...`).
- [ ] L'image Docker se construit et démarre (`docker build` + `docker
      run`), le healthcheck passe. **Non vérifié dans cette session**
      (pas de daemon Docker disponible dans le bac à sable) : à tester
      sur votre machine ou directement via le déploiement Coolify.
- [x] Le README documente les variables d'environnement, le point de
      montage réservé pour le futur volume SQLite, et les étapes
      Tailscale pour un accès mobile en HTTPS.
- [x] Aucun secret dans le dépôt (`.env` ignoré par git, seul
      `.env.example` est versionné).
- [ ] Accès réel depuis un téléphone via Tailscale. **Non vérifié**,
      nécessite le déploiement Coolify réel, à la charge du propriétaire.

## Journal

- **23/10/2026** — Recherche préalable (Lightweight Charts v5, licence
  Apache-2.0, confirmée sans restriction géographique ; Tailscale retenu
  en plan A, HTTPS valide pour l'installation PWA future, pas de
  restriction identifiée depuis la France). Lightweight Charts v5.2.1
  vendorisé directement dans le dépôt (`static/vendor/`) plutôt que
  chargé depuis un CDN, pour que l'application fonctionne entièrement en
  réseau privé (Tailscale) sans dépendance Internet au runtime.
- **23/10/2026** — Squelette codé : FastAPI (`app/main.py`), données de
  démonstration figées et explicitement signalées comme telles dans
  l'interface (`app/fixtures.py`), page mobile-first en mode sombre
  (`static/`), Dockerfile avec utilisateur non root et healthcheck,
  workflow CI (tests uniquement, pas de build Docker en CI pour l'instant),
  README de déploiement Coolify + guide Tailscale pas à pas. Tests
  automatisés (5) exécutés en local, verts. Build Docker non vérifié
  (pas de daemon Docker dans le bac à sable de la session) ; à vérifier
  avant de considérer le P0 terminé.
