# Analyse technique crypto

Outil personnel d'analyse technique crypto, inspiré de la méthode publique
de V. Ganne. Lecture seule : aucun ordre, aucune clé d'exchange.

État actuel : **P0** (squelette) — voir
`docs/cahiers-des-charges/README.md` pour le suivi complet par phase.

## Développement local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

Page de test : http://127.0.0.1:8000 (données de démonstration figées,
pas une donnée de marché réelle en P0).

## Déploiement Coolify

1. **Nouvelle ressource** dans Coolify → Application → source : ce dépôt
   GitHub (`antoinelabet4/analyse_technique`), branche `main`.
2. **Build** : Dockerfile détecté automatiquement (`Dockerfile` à la
   racine). Port exposé par le conteneur : `8000`.
3. **Variables d'environnement** (onglet Environment Variables) : copier
   `.env.example` et renseigner les valeurs réelles. Aucune n'est encore
   utilisée en P0 (`ANTHROPIC_API_KEY`, `LLM_MODEL` sont prévues pour les
   phases suivantes) ; les déclarer dès maintenant évite une étape
   manuelle plus tard.
4. **Limites mémoire/CPU** (onglet Resources) : poste partagé avec
   n8n/PostgreSQL/Immich sur 16 Go de RAM, cette application n'a pas
   besoin de plus de 256 Mo de RAM / 0,5 CPU en P0. À ajuster quand le
   moteur d'analyse (P1) et le cache seront en place.
5. **Volume persistant** : monter un volume sur `/app/data` (déclaré
   dans le `Dockerfile`, réservé au futur cache/historique SQLite ; vide
   et inutilisé en P0).
6. **Healthcheck** : Coolify lit le `HEALTHCHECK` du Dockerfile
   (`/health`) automatiquement, rien à configurer en plus.
7. **Déployer**, puis vérifier `https://<url-interne-coolify>/health` →
   `{"status":"ok"}`.

## Accès mobile via Tailscale (plan A)

Objectif : accéder à l'application depuis le téléphone, en HTTPS valide
(nécessaire pour l'installation PWA future), sans ouvrir de port sur la
box.

1. Installer Tailscale sur le mini PC Ubuntu (`curl -fsSL
   https://tailscale.com/install.sh | sh`, puis `tailscale up`) et sur le
   téléphone (app officielle), avec le même compte.
2. Dans la console d'admin Tailscale (https://login.tailscale.com/admin/dns) :
   activer **MagicDNS** puis **HTTPS Certificates** (onglet DNS). Cela
   permet d'obtenir un certificat Let's Encrypt valide pour le nom
   `<machine>.<tailnet>.ts.net`.
3. Faire pointer un reverse proxy local (ou directement Coolify si son
   proxy intégré le permet) vers ce nom de domaine Tailscale et le port
   exposé par l'application.
4. Depuis le téléphone (connecté au tailnet), ouvrir
   `https://<machine>.<tailnet>.ts.net` : le cadenas HTTPS doit être
   valide (pas d'avertissement de certificat).
5. Garder Plan B (Cloudflare Tunnel + Access) en réserve si un accès sans
   client Tailscale installé devient nécessaire (partage avec un tiers,
   domaine déjà géré par Cloudflare).

Cette étape n'est pas automatisée par l'agent : à réaliser et valider par
le propriétaire, cette procédure servant de guide pas à pas.

## Licence et attribution

Le graphique utilise TradingView Lightweight Charts™ (Apache-2.0),
vendorisé dans `static/vendor/`. Voir le fichier `NOTICE` pour le détail
de l'attribution requise.
