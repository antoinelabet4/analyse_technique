# Cahiers des charges — suivi du projet

Chaque phase du plan (P0 a P3, voir `CLAUDE.md`) a son propre cahier des
charges dans ce dossier. Un cahier des charges repond a trois questions et
est tenu a jour au fil du travail, pas ecrit une fois puis oublie :

- **Ou on va** : objectif et perimetre, decides avant de coder.
- **Ou on en est** : etat d'avancement, mis a jour a chaque avancee reelle.
- **Comment on sait que c'est fini** : criteres de validation verifiables,
  pas des impressions.

## Format d'un cahier des charges

Chaque fichier suit la meme structure :

1. **Objectif** — un paragraphe, le probleme resolu.
2. **Perimetre** — ce qui est inclus, et explicitement ce qui ne l'est pas.
3. **Etat d'avancement** — `A faire` / `En cours` / `Fait`, avec la date.
4. **Criteres de validation** — une liste verifiable (test qui passe,
   comportement observe), pas "ca a l'air de marcher".
5. **Journal** — les decisions prises en cours de route et pourquoi, dans
   l'ordre chronologique. C'est la partie qui repond a "pourquoi c'est fait
   comme ca" plus tard.

Nommage : `P0-nom-de-la-phase.md`, `P1-nom-de-la-phase.md`, etc. Une phase
peut avoir plusieurs cahiers si son perimetre se decoupe naturellement
(ex. P2 derives / P2 macro).

## Suivi global

| Phase | Cahier des charges | Etat |
| - | - | - |
| P0 | Squelette Docker + acces mobile | A faire |
| P1 | MVP : moteur deterministe + texte + graphique (5 actifs) | A faire |
| P2 | Derives (funding, OI, options) et macro (F&G, dominance, DXY, S&P) | A faire |
| P3 | On-chain, lignes de tendance, declenchement n8n | A faire |

Ce tableau est mis a jour a chaque fois qu'un cahier des charges change
d'etat.

## Ce qui reste bloque sur une decision ou une demarche du proprietaire

- **Choix definitif Tailscale vs Cloudflare Tunnel** : Tailscale retenu en
  plan A (voir recherche du 23/10/2026, aucun blocage identifie depuis la
  France), a confirmer une fois le P0 deploye sur Coolify.
- **Fiabilite Binance spot/futures depuis une IP francaise** : risque
  identifie lie au retrait MiCA (juillet 2026) ; Kraken doit etre un
  fallback reellement operationnel, pas seulement documente, teste en
  conditions reelles avant la fin du P1.
- **Source gratuite fiable pour DXY et S&P 500** (P2) : aucune source
  sans cle confirmee a ce jour (Stooq semble desormais exiger une cle) ;
  a tester en direct depuis le serveur avant d'ecrire le code du P2, et
  afficher "source indisponible" plutot que d'inventer la donnee si aucune
  ne fonctionne.
- **Verification directe de la doc officielle Deribit** (P2) : seule une
  source tierce (scraper) a ete consultee a ce jour, pas docs.deribit.com.
