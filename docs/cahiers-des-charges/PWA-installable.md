# PWA installable

## Objectif

Permettre d'installer l'app sur l'écran d'accueil du téléphone (icône,
plein écran, sans barre d'adresse), sans App Store ni Expo — déjà prévu
dans le brief d'origine ("PWA installable (manifest, icône, écran
d'accueil)"), implémenté après le P1 et le P2 sur demande du
propriétaire (24/10/2026).

## Périmètre

- Inclus : `manifest.json`, icônes (192/512/512 maskable/180 Apple),
  balises `<meta>` Apple (Safari iOS n'utilise pas pleinement le
  manifest), service worker minimal (requis pour l'installabilité
  Chrome/Android, aucune mise en cache hors-ligne pour l'instant).
- Non inclus : mise en cache hors-ligne / "dernière analyse affichée
  immédiatement, recalcul en arrière-plan" (du brief d'origine) —
  nécessite une vraie stratégie de cache applicatif dans le service
  worker, reportée pour ne pas risquer de servir une donnée de marché
  périmée sans le signaler clairement. À reprendre si besoin plus tard.

## État d'avancement

**Fait pour la portée retenue — 24/10/2026.**

## Critères de validation

- [x] `manifest.json` servi à la racine (`/manifest.json`), portée `/`.
- [x] Service worker servi à la racine (`/sw.js`), portée `/` confirmée
      (`registration.scope`), actif après chargement.
- [x] Icônes générées localement (pas de dépendance à un service
      externe), servies et testées (192, 512, 512 maskable, 180 Apple).
- [x] Balises Apple (`apple-mobile-web-app-capable`,
      `apple-touch-icon`, etc.) présentes pour Safari iOS, cas d'usage
      réel du propriétaire.
- [ ] Installation réelle "Ajouter à l'écran d'accueil" testée sur
      l'iPhone du propriétaire — à faire de son côté, pas vérifiable
      depuis cet environnement.

## Journal

- **24/10/2026** — Icônes générées par script (PIL), motif de
  chandeliers stylisé cohérent avec le thème de l'app, pas d'image
  externe. Service worker et manifest volontairement servis depuis la
  racine (`/manifest.json`, `/sw.js`), pas depuis `/static/`, pour que
  leur portée couvre toute l'app (sinon un service worker à
  `/static/sw.js` n'aurait par défaut qu'une portée `/static/`, ce qui
  aurait échoué aux critères d'installabilité Chrome). Vérifié dans un
  vrai navigateur : service worker actif avec portée `/`, manifest lié
  correctement, aucune régression visuelle. 96 tests passent.
