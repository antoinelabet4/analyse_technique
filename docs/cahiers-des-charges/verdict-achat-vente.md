# Verdict achat/vente explicite dans le texte LLM

## Objectif

Demande explicite du propriétaire (25/10/2026), après confirmation que
l'usage reste strictement personnel (pas de clients, pas de diffusion) :
le texte explicatif LLM tranche désormais avec un verdict assumé
("acheter", "vendre" ou "attendre"), en plus des 5 sections de texte
existantes. Jusqu'ici le projet interdisait explicitement tout "conseil
d'achat ou de vente" (brief d'origine, disclaimer, reformulation
"zone d'opportunité/risque" du 24/10/2026) ; ce cahier documente le
changement de principe et son périmètre exact, tel que validé par le
propriétaire (`AskUserQuestion`, 25/10/2026).

## Périmètre

- Inclus :
  - Nouvelle clé `"verdict"` dans la réponse JSON du LLM, contrainte à
    exactement une valeur parmi `"acheter"`, `"vendre"`, `"attendre"` (pas
    de texte libre : une invention ici ne serait pas vérifiable comme un
    chiffre, donc on contraint au moins sa forme).
  - Le verdict doit être basé uniquement sur les données déjà présentes
    dans le JSON "facts" (régime, niveaux les plus proches, RSI14, MACD,
    position dans le nuage Ichimoku), jamais sur une information externe.
  - Affichage en badge distinct (vert/rouge/gris) au-dessus du texte,
    jamais mélangé aux 5 sections existantes.
  - Disclaimer reformulé partout où il apparaît (footer, carte d'analyse) :
    ne dit plus "ce n'est pas un conseil financier" (devenu faux), dit à la
    place que l'analyse est générée par IA, à usage personnel, et que le
    verdict peut se tromper.
  - Rejet et réessai automatique (même mécanique que pour les chiffres
    inventés) si le verdict renvoyé n'est pas l'une des trois valeurs
    exactes attendues.
- Non inclus :
  - Aucune garantie que le verdict est "correct" : contrairement aux
    chiffres, un jugement ne peut pas être vérifié automatiquement contre
    les facts. Seule sa forme (une des 3 valeurs) est contrôlée.
  - Pas de changement pour un usage multi-utilisateur ou partagé : ce
    changement de principe est spécifique à l'usage personnel confirmé par
    le propriétaire, à reconsidérer si le projet évoluait vers un usage
    partagé un jour.
  - Le résumé en chiffres bruts (`#resume`, sans LLM) ne contient aucun
    verdict et garde son disclaimer "pas un conseil financier" d'origine,
    qui reste exact pour cette section (pure lecture de données, aucun
    jugement).

## État d'avancement

**Fait — 25/10/2026.**

## Critères de validation

- [x] Le JSON renvoyé par le LLM contient une clé `verdict` valant
      exactement `"acheter"`, `"vendre"` ou `"attendre"`.
- [x] Une réponse LLM avec un verdict absent ou hors de ces 3 valeurs est
      rejetée et réessayée automatiquement une fois, comme pour un chiffre
      inventé.
- [x] Le badge s'affiche avec la bonne couleur selon le verdict (vert
      acheter, rouge vendre, gris attendre).
- [x] Le disclaimer ne prétend plus "pas un conseil financier" là où un
      verdict est affiché.

## Journal

- **25/10/2026** — Confirmé par `AskUserQuestion` : badge dédié (pas
  intégré aux sections de texte existantes) et disclaimer reformulé
  honnêtement. `PROMPT_SYSTEME` et `_appeler_llm` modifiés
  (`app/llm/analysis.py`) : validation stricte du verdict (une des 3
  valeurs exactes, sinon `TexteNonFiable` et réessai automatique, même
  mécanique que pour les chiffres absents des facts). Frontend
  (`static/app.js`, `static/style.css`, `static/index.html`) : badge
  `.badge-verdict` avec 3 variantes de couleur, disclaimers reformulés
  dans le footer et la carte d'analyse (le résumé en chiffres bruts,
  lui, garde son disclaimer d'origine, toujours exact puisqu'il ne
  contient aucun verdict). Vérifié par Playwright avec une réponse LLM
  simulée (les 3 valeurs de verdict, rendu visuel du badge). 132 tests
  backend passent, dont 3 nouveaux sur la validation du verdict dans
  `_appeler_llm` (absent, hors liste, les 3 valeurs valides acceptées).
  Non vérifiable avec un vrai appel LLM depuis cette session (pas de
  clé API ici) : à confirmer par le propriétaire après redéploiement,
  y compris sur la pertinence réelle du verdict rendu (la forme est
  garantie, pas la justesse du jugement).
