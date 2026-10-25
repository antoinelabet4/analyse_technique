# Verdict achat/vente explicite dans le texte LLM

## Objectif

Demande explicite du propriétaire (25/10/2026), après confirmation que
l'usage reste strictement personnel (pas de clients, pas de diffusion) :
le texte explicatif LLM tranche désormais avec un verdict assumé, en
plus des 5 sections de texte existantes. Jusqu'ici le projet interdisait
explicitement tout "conseil d'achat ou de vente" (brief d'origine,
disclaimer, reformulation "zone d'opportunité/risque" du 24/10/2026) ;
ce cahier documente le changement de principe et son périmètre exact,
tel que validé par le propriétaire (`AskUserQuestion`, 25/10/2026).

Évolution le même jour (toujours 25/10/2026) : le propriétaire a fait
remarquer qu'un verdict "acheter"/"vendre" brut est ambigu sans savoir
si on détient déjà l'actif ("zone de risque n'est pas clair... ce n'est
pas une zone d'achat [si on détient déjà]"). Le LLM calcule donc
maintenant un **signal technique pur** ("haussier", "baissier" ou
"neutre", jamais une action), et c'est le frontend qui le traduit en
action selon un réglage "je détiens / je ne détiens pas" par actif,
mémorisé sur l'appareil — voir périmètre et journal ci-dessous.

## Périmètre

- Inclus :
  - Nouvelle clé `"verdict"` dans la réponse JSON du LLM, contrainte à
    exactement une valeur parmi `"haussier"`, `"baissier"`, `"neutre"`
    (pas de texte libre : une invention ici ne serait pas vérifiable
    comme un chiffre, donc on contraint au moins sa forme). Ce signal est
    uniquement technique : le LLM ne connaît pas la position de
    l'utilisateur et ne doit jamais en supposer une.
  - Le signal doit être basé uniquement sur les données déjà présentes
    dans le JSON "facts" (régime, niveaux les plus proches, RSI14, MACD,
    position dans le nuage Ichimoku), jamais sur une information externe.
  - Réglage "je détiens déjà / je ne détiens pas" par actif (case à
    cocher sous le sélecteur d'actif, mémorisé en localStorage).
  - Traduction du signal en action, côté client, selon la position :
    haussier + pas détenu → "Acheter" ; haussier + détenu → "Conserver" ;
    baissier + détenu → "Vendre" ; baissier + pas détenu → "Attendre" ;
    neutre (quelle que soit la position) → "Attendre". Changer le réglage
    de position recalcule le badge affiché instantanément, sans nouvel
    appel réseau (le signal du dernier résultat LLM est conservé côté
    client pour cette traduction).
  - Affichage en badge distinct (vert/rouge/gris/bleu) au-dessus du
    texte, jamais mélangé aux 5 sections existantes.
  - Disclaimer reformulé partout où il apparaît (footer, carte d'analyse) :
    ne dit plus "ce n'est pas un conseil financier" (devenu faux), dit à la
    place que l'analyse est générée par IA, à usage personnel, et que le
    verdict peut se tromper.
  - Rejet et réessai automatique (même mécanique que pour les chiffres
    inventés) si le signal renvoyé n'est pas l'une des trois valeurs
    exactes attendues.
  - Cache LLM versionné (`PROMPT_VERSION`) pour qu'un changement de
    prompt (comme celui-ci) invalide immédiatement les textes déjà en
    cache, plutôt que de continuer à servir l'ancienne version jusqu'à la
    clôture de la bougie en cours.
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
- **25/10/2026 (suite, deux bugs réels trouvés en production)** :
  - **Cache jamais invalidé par un changement de prompt.** Le texte
    rendu restait celui généré avec l'ancien prompt (sans verdict, plus
    long) des heures après le déploiement du nouveau, car le cache
    SQLite était indexé uniquement par (actif, timeframe, dernière
    bougie), jamais par une version de prompt. Corrigé par
    `PROMPT_VERSION` (table `analyses_llm_v2`, nouvelle colonne
    `version` dans la clé primaire) : incrémenté à chaque changement de
    `PROMPT_SYSTEME` qui modifie le texte produit.
  - **Verdict ambigu sans connaître la position.** Signalé par le
    propriétaire : "zone de risque n'est pas clair, si ça monte c'est
    bien si je détiens mais ce n'est pas une zone d'achat". Confirmé par
    `AskUserQuestion` : réglage de position par actif plutôt que
    reformuler le texte sans contexte. Renommé "acheter/vendre/attendre"
    en "haussier/baissier/neutre" dans le JSON du LLM (signal technique
    pur, le LLM ignore la position) ; ajout de `calculerLibelleVerdict`
    côté client qui traduit signal + position en l'action affichée.
    `PROMPT_VERSION` incrémenté en même temps (3), pour que ce
    changement de vocabulaire ne soit pas lui non plus bloqué par
    l'ancien cache.
  Vérifié par Playwright : les 6 combinaisons signal × position
  affichent le badge attendu (haussier/pas détenu → Acheter,
  haussier/détenu → Conserver, baissier/détenu → Vendre, baissier/pas
  détenu → Attendre, neutre → Attendre dans les deux cas). 133 tests
  backend passent, dont un nouveau sur l'invalidation du cache par
  changement de `PROMPT_VERSION`.
- **25/10/2026 (suite 2)** — Signalé par le propriétaire : "Zone
  d'opportunités et risques sont toujours identique que je détienne ou
  pas la crypto". Bug réel, oublié lors du correctif précédent : le
  badge verdict avait bien été rendu dépendant de la position
  (`calculerLibelleVerdict`), mais les **zones colorées sur le
  graphique** et la section "Zones" du résumé texte (dérivées
  directement des niveaux de pivot, indépendamment du LLM) étaient
  restées sur l'ancienne logique fixe : support toujours vert
  ("opportunité"), résistance toujours rouge ("risque"), quelle que
  soit la position. Corrigé par `estZoneOpportunite(estSupport,
  detient)` (`static/app.js`) : si on ne détient pas, un support reste
  une opportunité d'entrée et une résistance un risque de payer trop
  cher (comportement d'origine) ; si on détient déjà, c'est inversé —
  une résistance devient l'opportunité de prise de profit, un support
  le risque de voir la position perdre de la valeur. Appliqué aux
  bandes du graphique (`dessinerZonesNiveaux`) et à la section "Zones"
  du résumé (`afficherResume`), toutes deux recalculées instantanément
  au changement du réglage "Je détiens", sans nouvel appel réseau.
  Vérifié par Playwright : les couleurs des bandes s'inversent
  exactement à l'activation du réglage, texte du résumé cohérent.
  Changement purement frontend, 139 tests backend toujours verts.
