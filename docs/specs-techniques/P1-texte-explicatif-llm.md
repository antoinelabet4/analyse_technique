# Spec technique : texte explicatif LLM + déclenchement manuel

Cahier associé : docs/cahiers-des-charges/P1-mvp-moteur-texte-graphique.md
Statut : validé le 24/10/2026 par le propriétaire (plafond 20 appels/jour, débit 10s minimum entre deux clics)

## Besoin

Générer, à partir du JSON "facts" déjà produit par `app/engine/facts.py`,
un texte explicatif en français simple (sections Tendance / Niveaux à
surveiller / Scénarios / Ce qui changerait l'analyse / Risques), **sans
appel automatique à chaque changement d'actif ou de timeframe** : le
déclenchement est manuel, via un bouton "Lancer l'analyse" superposé au
graphique, pour maîtriser le coût (demande explicite du propriétaire,
24/10/2026).

## Comportement du bouton (interface)

- À chaque changement d'actif ou de timeframe, le bouton revient dans un
  état "pas encore lancé" (grisé/inactif visuellement), et tout texte
  explicatif précédemment affiché est masqué — jamais laissé affiché
  comme s'il correspondait au nouvel actif sélectionné.
- Un clic déclenche l'appel à l'API (section suivante) et passe le
  bouton dans un état "en cours" (chargement).
- Si une analyse déjà en cache existe pour cet actif/timeframe/bougie
  clôturée (voir cache ci-dessous), le texte s'affiche immédiatement,
  sans nouvel appel LLM, et le bouton l'indique (ex. "Analyse à jour").

## Cache des analyses

Table SQLite dédiée (même fichier `/app/data/cache.db` que le cache de
marché, table séparée `analyses_llm`), clé = (actif, timeframe,
horodatage de la dernière bougie clôturée utilisée). Une nouvelle bougie
clôturée invalide le cache pour cette clé (conforme au brief : "une
analyse par actif et par bougie clôturée"). Cela répond aussi à
l'optimisation différée dans `docs/specs-techniques/P1-recuperation-donnees.md`
("pas encore spécifiée") : c'est cette couche-ci.

## Contrat d'API

- `POST /api/analysis-llm/{actif}/{timeframe}` : construit les "facts"
  (réutilise `build_facts`), vérifie le cache ; si absent ou périmé,
  appelle le LLM avec un prompt système qui :
  - interdit tout chiffre absent du JSON "facts" fourni ;
  - interdit toute prédiction de prix, ton péremptoire, conseil d'achat
    ou de vente (conforme au brief) ;
  - impose les 5 sections demandées.
  Puis **contrôle automatique** : chaque nombre présent dans le texte
  généré doit être retrouvable dans le JSON "facts" (comparaison
  textuelle sur les valeurs numériques). Si le contrôle échoue, une
  seule regénération est tentée ; si elle échoue encore, l'endpoint
  renvoie une erreur explicite ("texte non fiable, non affiché") plutôt
  que de servir un texte non conforme.
- Réponse : `{texte: {tendance, niveaux, scenarios, ce_qui_changerait, risques}, source_cache: bool, genere_le: datetime}`.

## Garde-fous de coût (validés le 24/10/2026)

- **Plafond quotidien d'appels LLM : 20 appels/jour.** Compteur
  journalier dans SQLite (table `llm_usage`, reset à minuit UTC).
- **Limitation de débit : 10 secondes minimum entre deux appels**
  (verrou global, usage solo donc pas de distinction par IP/session).
- Au-delà du plafond ou en cas de débit dépassé, le bouton affiche
  clairement "Plafond quotidien atteint (20/jour)" / "Veuillez
  patienter quelques secondes", jamais une erreur générique.

## Garde-fous

- Clé `ANTHROPIC_API_KEY` lue uniquement depuis l'environnement, jamais
  en dur, jamais journalisée.
- Modèle lu depuis `LLM_MODEL` (déjà dans `.env.example`,
  `claude-sonnet-5-5` par défaut, conforme au brief d'origine).
- Timeout explicite sur l'appel LLM (ex. 30s), erreur explicite affichée
  si dépassé, jamais un texte partiel présenté comme complet.

## Plan de test

- `test_llm_facts_check.py` : fonction de contrôle "chaque nombre du
  texte est dans les facts", testée avec un texte conforme (passe) et un
  texte contenant un chiffre inventé (échoue), données figées.
- `test_llm_cache.py` : deuxième appel sur la même bougie clôturée sert
  le cache, pas de nouvel appel LLM (mocké).
- `test_llm_plafond.py` : au-delà du plafond configuré, l'endpoint
  refuse avec un message explicite, pas d'appel LLM déclenché.
- Appel LLM réel lui-même non testé en CI (coût, non déterministe) ;
  vérification manuelle ponctuelle documentée dans le cahier.
