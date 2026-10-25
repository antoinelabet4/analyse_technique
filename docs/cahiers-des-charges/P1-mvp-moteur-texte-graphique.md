# P1 — MVP : moteur déterministe + texte + graphique (5 actifs)

## Objectif

Afficher, pour BTC, ETH, XRP, TAO et RENDER, un graphique en chandeliers
annoté (niveaux, moyennes mobiles, Ichimoku, scénarios) avec en dessous un
texte explicatif en français simple, à partir de données réelles (Binance
en priorité, Kraken en secours) et d'un moteur de calcul entièrement
déterministe, sans aucun chiffre inventé.

## Périmètre

- Inclus : récupération des bougies 1D/1W (Binance, fallback Kraken),
  cache disque, indicateurs (MM 50/200j, EMA 200s, RSI 14, ATR 14,
  volume, **Ichimoku Kinko Hyo**), détection de pivots et regroupement en
  zones de support/résistance (y compris le nuage Ichimoku comme zone
  dynamique), détermination du régime de marché, scénarios haussier/
  baissier/range avec condition de clôture/cible/invalidation, force
  relative des alts vs BTC, texte explicatif généré par LLM à partir d'un
  JSON "facts" exclusivement, contrôle automatique qu'aucun chiffre du
  texte n'est absent de ce JSON.
- Non inclus : dérivés (funding, OI, options), macro (F&G, dominance,
  DXY, S&P), on-chain, authentification, PWA installable, déclenchement
  n8n. Ces points arrivent en P2/P3.

## État d'avancement

**Fait pour la portée retenue — 24/10/2026.** Moteur d'indicateurs/
niveaux/régime/scénarios, récupération de données réelles (Binance +
fallback Kraken + cache SQLite), force relative vs BTC, câblage API +
graphique mobile, nuage Ichimoku en vrai ruban coloré (SVG, suit
Senkou A/B dans le temps), et texte explicatif LLM avec déclenchement
manuel et contrôle automatique, codés, testés et vérifiés dans un vrai
navigateur (voir journal). Reste en discussion : certaines demandes
d'itération UI (zones toujours présentes, etc.), traitées séparément.

## Critères de validation

- [ ] Pour chacun des 5 actifs, en 1D et en 1W : les indicateurs
      (MM/EMA/RSI/ATR/Ichimoku) sont calculés et correspondent à un calcul
      de référence sur un jeu de données figé (test unitaire).
- [ ] Les niveaux affichés (pivots + nuage Ichimoku) sont les 2-3 supports
      et résistances les plus proches du prix courant, avec nombre de
      touches et éventuelle inversion de rôle.
- [ ] Chaque scénario affiché a une condition de clôture vérifiable, une
      cible (zone suivante) et un niveau d'invalidation, sans probabilité
      chiffrée inventée.
- [ ] Le texte explicatif ne contient aucun nombre absent du JSON "facts"
      (contrôle automatique testé avec un cas qui doit échouer sciemment).
- [ ] Si Binance échoue, la source bascule sur Kraken et l'interface
      affiche la source effectivement utilisée.

## Journal

- **23/10/2026** — Démarrage de la spec technique. Demande explicite du
  propriétaire d'intégrer l'Ichimoku Kinko Hyo, très utilisé dans la
  méthode de Vincent Ganne. Les réglages précis utilisés par Ganne ne
  sont pas une information publique vérifiable dont je dispose ; la spec
  part des réglages classiques (9/26/52/26) et ce point est marqué comme
  à confirmer avant validation définitive, pas comme un fait établi.
- **23/10/2026** — Spec validée ("Go"). `app/engine/indicators.py` codé :
  SMA/EMA/RSI/ATR, Ichimoku complet (nuage traité comme un niveau
  dynamique au même titre que les zones de pivots), détection de pivots
  et regroupement en zones avec tolérance ATR, inversion de rôle
  (heuristique documentée dans le docstring), régime de marché combinant
  MM/EMA longue et signaux Ichimoku sans score composite caché, scénarios
  haussier/baissier/range avec cible et invalidation (support/résistance
  ou Kijun selon le plus proche). 42 tests unitaires passent, données
  figées (déterministes), aucun appel réseau ni LLM dans ce module.
- **23/10/2026** — `app/data/market.py` codé : Binance (endpoint public
  `data-api.binance.vision`) en priorité, Kraken en secours, cache SQLite
  comme filet de sécurité si les deux échouent (jamais présenté comme une
  donnée fraîche : champ `perime: true`). Accessibilité vérifiée en
  conditions réelles depuis ce réseau pour les 5 actifs (BTC, ETH, XRP,
  TAO, RENDER) sur les deux sources, en 1D et en 1W. 52 tests passent
  (10 nouveaux : bascule de source, cache périmé, aucune source + aucun
  cache, parsing contre des réponses réellement capturées le 23/10/2026).
  Pipeline vérifié de bout en bout avec un appel réseau réel (hors suite
  automatisée). Note : l'optimisation "pas de rappel réseau si aucune
  bougie n'a clôturé" du brief d'origine est reportée à la couche de
  cache des analyses (pas encore spécifiée), ce module privilégiant
  toujours une donnée fraîche quand une source répond (voir spec).
- **24/10/2026** — Force relative vs BTC (`app/engine/relative_strength.py`,
  ratio actif/BTC sur 30 bougies), assemblage du JSON "facts"
  (`app/engine/facts.py`) et endpoints API (`/api/assets`,
  `/api/analysis/{actif}/{timeframe}`) codés. Interface mobile mise à
  jour : sélecteur d'actif, bascule 1D/1W, chandeliers réels, niveaux de
  prix (MM/EMA, nuage, supports/résistances) en overlay, résumé en
  sections repliables à partir des chiffres bruts (pas de texte LLM
  encore). Vérifié dans un vrai navigateur (Chromium headless, viewport
  mobile 390×844) : capture d'écran BTC/1D et ETH/1W conformes.
  **Bug trouvé et corrigé pendant cette vérification** : un clic rapide
  sur un actif puis un timeframe lançait deux requêtes concurrentes ; si
  la première répondait après la seconde, elle écrasait l'affichage avec
  des données périmées (ETH affiché avec les MM 1D au lieu de l'EMA200
  1W). Corrigé par un identifiant de requête qui ignore toute réponse
  devenue obsolète. 63 tests passent.
- **24/10/2026** — Itération interface suite au premier test réel sur le
  mini PC (déploiement Coolify + accès Tailscale confirmés fonctionnels) :
  - Ce qui semblait être un bug d'échelle qui ne se mettait pas à jour
    entre actifs était en fait l'absence d'indicateur de chargement
    pendant l'appel réseau réel à Binance (quelques secondes) : ajout
    d'un état de chargement visible (graphique assombri, badge "Chargement
    de X…").
  - Nuage Ichimoku et niveaux affichés comme de vraies bandes colorées
    remplies (overlay positionné via `priceToCoordinate`, resynchronisé au
    zoom/pan et au redimensionnement), plus seulement des lignes
    horizontales.
  - Ajout de **zones d'opportunité et de risque** sur le graphique,
    demandées par le propriétaire. Point de vigilance soulevé par l'agent
    avant implémentation : le brief interdit tout "conseil d'achat ou de
    vente". Le propriétaire a tranché le 24/10/2026 : reformulation sans
    ces mots ("Zone d'opportunité" / "Zone de risque"), dérivées des
    cibles déjà calculées par les scénarios haussier/baissier existants
    (mêmes chiffres que la section Scénarios, aucune donnée nouvelle
    inventée).
  - Sélecteur d'actif remplacé par un menu déroulant (anticipe l'ajout de
    tous les actifs disponibles sur TradingView, hors périmètre pour
    l'instant).
  - Toute mention de Vincent Ganne retirée de l'interface (sur demande
    explicite), disclaimer reformulé : "Analyse technique automatisée,
    générée automatiquement. Ce n'est pas un conseil financier."
  - Passe de design pour un rendu plus "app" (en-tête collant, cartes
    arrondies, select natif stylé, transitions douces).
  - Vérifié dans un vrai navigateur (chargement, bascule d'actif avec
    zoom/pan, positionnement des bandes). 63 tests toujours verts (aucun
    changement backend).
- **24/10/2026** — Texte explicatif LLM codé (`app/llm/analysis.py`,
  `app/llm/facts_check.py`) : bouton "Lancer l'analyse" superposé au
  graphique (demande explicite du propriétaire, pour maîtriser le coût,
  jamais d'appel automatique), réinitialisé à chaque changement
  d'actif/timeframe. Cache SQLite par bougie clôturée, plafond quotidien
  20 appels/jour, débit minimum 10s entre deux appels (valeurs validées
  par le propriétaire le 24/10/2026, non devinées — voir CLAUDE.md
  "jamais deviner"). Contrôle automatique : chaque nombre du texte généré
  doit être retrouvable dans le JSON "facts" (tolérance d'arrondi,
  périodes d'indicateurs comme "RSI14" exemptées), une regénération
  tentée en cas d'échec, sinon erreur explicite jamais un texte non
  fiable affiché. 79 tests passent (appel LLM réel non testé en CI,
  vérifié manuellement que l'absence de clé API produit une erreur
  propre côté interface, sans fuite de détail interne).
- **24/10/2026** — Nuage Ichimoku redessiné en vrai ruban coloré (SVG
  superposé, polygones suivant Senkou A/Senkou B dans le temps, vert si
  haussier/rouge si baissier), sur demande explicite du propriétaire
  avec référence visuelle (illustration Binance Academy). Le backend
  expose désormais la série complète (`ichimoku.nuage_serie`), pas
  seulement les valeurs actuelles. Bug de rendu trouvé et corrigé
  pendant la vérification : le SVG ne s'affichait pas malgré des
  coordonnées correctes, à cause des `z-index` explicites posés par les
  canvas internes de Lightweight Charts sur les bougies — un `z-index`
  explicite sur notre SVG résout le conflit d'empilement. Limite connue,
  non traitée pour l'instant : le nuage ne se projette pas au-delà de la
  dernière bougie (projection future), seule la partie historique est
  dessinée.
- **25/10/2026** — Premier test réel en production après ajout de
  `ANTHROPIC_API_KEY` sur Coolify : le bouton "Lancer l'analyse" échouait
  toujours (502), sans aucune trace exploitable côté serveur (l'exception
  était interceptée dans `/api/analysis-llm` sans jamais être journalisée
  — correctif immédiat : `logger.exception(...)` + `logging.basicConfig`
  explicite). Une fois les logs lisibles, deux pannes réelles identifiées
  avec la trace complète : une réponse LLM tronquée en plein milieu d'une
  chaîne JSON (`JSONDecodeError: Unterminated string`), puis une réponse
  texte totalement vide (`Expecting value: line 1 column 1`) — toutes
  deux cohérentes avec un budget de tokens insuffisant (`max_tokens=1500`)
  si le modèle consomme des tokens de raisonnement avant le texte JSON
  visible. Correctifs : `max_tokens` porté à 4096 ; `_appeler_llm` détecte
  maintenant explicitement une réponse non interprétable (JSON invalide)
  et lève une `TexteNonFiable` avec le `stop_reason` et la taille reçue
  en diagnostic, au lieu de laisser remonter une `JSONDecodeError` sans
  contexte ; `generer_analyse` réessaie une fois automatiquement sur ce
  type d'échec (même logique que le réessai déjà en place pour le
  contrôle des chiffres). Non vérifié en conditions réelles à ce stade
  (pas d'accès direct à l'environnement de production depuis cette
  session) : le propriétaire doit confirmer après redéploiement que
  l'analyse aboutit, sinon renvoyer les nouveaux logs runtime. 120 tests
  passent, dont deux nouveaux qui rejouent précisément les deux pannes
  observées (réponse tronquée, réponse vide) et un qui vérifie le
  réessai automatique.
- **25/10/2026 (suite)** — `max_tokens` déployé (confirmé par le
  changement de symptôme : le 502 suivant provenait du contrôle des
  chiffres, pas d'une réponse tronquée), mais nouveau rejet signalé :
  "Le texte généré contient des chiffres absents des données ([-25.0,
  -18.0, -10.0, -5.0, 7.48, 500.0, 2026.0])". Diagnostic : la regex de
  détection de nombres (`_NOMBRE_RE`) lisait le tiret séparateur d'une
  date ISO ("2026-10-25") comme un signe moins, produisant -10 et -25 à
  partir d'une simple date mentionnée dans le texte généré (ex. "à jour
  au 2026-10-25") ; par ailleurs "2026" seul était rejeté car les facts
  ne contiennent cette année qu'à l'intérieur d'une chaîne de date,
  jamais comme nombre brut, et la fonction d'extraction ne regardait que
  les valeurs numériques, pas les chaînes. Deux correctifs ciblés :
  lookbehind négatif sur la regex pour ne plus confondre tiret de date et
  signe moins, et extraction des nombres aussi à l'intérieur des chaînes
  du JSON "facts" (dates notamment). Le prompt système a aussi été
  renforcé (interdiction explicite des pourcentages/calculs dérivés et
  des dates inventées) en mitigation supplémentaire pour les chiffres
  restants non expliqués par ce bug (7.48, 500.0), qui pourraient être de
  réelles inventions du modèle. 123 tests passent, dont deux nouveaux qui
  rejouent exactement le rejet constaté en production avec une date ISO.
  Non vérifiable en conditions réelles depuis cette session (pas d'accès
  à l'environnement de production) : à confirmer par le propriétaire
  après redéploiement.
- **25/10/2026 (suite 2)** — Après déploiement du correctif précédent,
  liste des chiffres rejetés réduite à `[-5.0, 7.78]` (contre 7 chiffres
  avant) : confirme que les deux bugs de dates étaient bien la cause
  principale. Les deux chiffres restants semblent de vraies inventions
  du modèle malgré le prompt renforcé. Cause identifiée : le réessai
  automatique rappelait le LLM avec exactement le même prompt que le
  premier essai, sans jamais lui dire quels chiffres avaient été
  rejetés — le laissant répéter la même erreur. `_appeler_llm` accepte
  maintenant un paramètre `chiffres_a_eviter`, ajouté au prompt système
  du réessai pour lister explicitement les chiffres fautifs et demander
  une relecture. 124 tests passent, dont un nouveau qui vérifie que le
  réessai reçoit bien la liste exacte des chiffres rejetés par le
  premier essai. Non vérifiable en conditions réelles depuis cette
  session : à confirmer par le propriétaire après redéploiement.
- **25/10/2026 (suite 3)** — Correctif du réessai déployé et confirmé
  actif (le rejet suivant ne contenait plus qu'un seul chiffre, `[-5.0]`,
  au lieu de deux) : le réessai a donc bien reçu le chiffre à éviter et
  en a quand même produit un autre. À ce stade, ce dernier chiffre
  ressemble à une vraie invention ponctuelle du modèle que le contrôle
  bloque correctement (comportement voulu : jamais de chiffre non
  vérifié affiché, quitte à devoir relancer l'analyse). Par ailleurs,
  l'en-tête restait caché sous la barre de statut malgré le correctif
  CSS déployé : cause probable identifiée, aucun `Cache-Control`
  explicite n'était envoyé pour l'HTML/CSS/JS/manifest/service worker,
  et Safari iOS en PWA installée peut continuer à servir une version
  périmée de ces fichiers après un redéploiement plutôt que de
  revalider. Ajout d'un middleware qui force `Cache-Control: no-cache`
  sur ces routes (revalidation systématique via l'ETag déjà émis par
  `StaticFiles`, pas de `no-store` pour ne pas perdre le bénéfice du
  304). 125 tests passent, dont un nouveau qui vérifie l'en-tête sur
  toutes les routes concernées. Non vérifiable en conditions réelles
  depuis cette session (pas d'iPhone disponible) : à confirmer par le
  propriétaire après redéploiement, en quittant complètement puis en
  relançant la PWA installée (pas seulement la remettre au premier
  plan) pour forcer un rechargement complet.
