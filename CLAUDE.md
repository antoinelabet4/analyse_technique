# Instructions pour toute session de developpement sur ce projet

Regles de construction de code reprises et adaptees du depot `host-ai`
(demande explicite du proprietaire, 23/10/2026). Projet solo, usage
personnel, pas de clients ni de donnees multi-tenant : les regles
ci-dessous sont simplifiees en consequence par rapport a leur version
d'origine.

## Principe directeur : Definition of Done validee avant de coder

Avant toute modification de code, l'agent presente et fait valider avec
le proprietaire une Definition of Done (ou, pour ce projet, le plan de
phase decrit dans le cahier des charges correspondant). Elle liste de
facon concrete et exhaustive ce que l'agent doit modifier, et uniquement
ce qu'il doit modifier. Aucune branche ni aucun fichier de production
n'est modifie avant cette validation explicite.

La Definition of Done distingue au minimum : le resultat observable
attendu, le perimetre inclus, le perimetre explicitement exclu, les
actions qui restent a la charge du proprietaire (cles API, configuration
Coolify/Tailscale, decisions de deploiement), les donnees dont la source
doit etre affichee honnetement si elle manque, et la recette qui
demontrera le resultat. Si un point est ambigu ou implique un choix
produit, l'agent demande une clarification au lieu de l'elargir de sa
propre initiative.

Toute modification de comportement livre aussi un test de non-regression
au niveau adapte au risque (test unitaire sur le moteur deterministe,
verification manuelle documentee pour l'interface). Le test decrit le
resultat attendu, y compris ce qui ne doit pas se produire.

Un correctif mineur ou urgent (une ligne, une configuration, une faute)
peut etre fait sans Definition of Done detaillee a condition de
l'annoncer comme tel avant de le faire et de livrer son test. Tout le
reste exige la validation prealable.

## Principe directeur : pas de nouveau developpement sans cahier + spec technique validee

Un cahier des charges (`docs/cahiers-des-charges/`) decrit le besoin pour
une phase (P0 a P3, voir le plan du projet) mais ne suffit pas seul a
lancer un developpement.

- Toute nouvelle fonctionnalite a, en plus du cahier, une fiche dans
  `docs/specs-techniques/` (schema de donnees, contrat d'API/de fonction,
  garde-fous, plan de test) **validee par le proprietaire avant
  l'ecriture du code**.
- Une exception n'est possible que pour un correctif urgent ou mineur, et
  seulement si elle est annoncee explicitement comme telle. Le cahier et
  la spec sont alors completes immediatement apres, jamais reportes.
- Gabarits : `docs/cahiers-des-charges/README.md` et
  `docs/specs-techniques/README.md`.

## Principe directeur : jamais deviner, soit on sait soit on ne sait pas

A la demande explicite du proprietaire (24/10/2026), reformulation
renforcee du principe "aucune donnee inventee" ci-dessous, etendue a
toute incertitude, pas seulement aux chiffres de marche : si une
information n'est pas verifiee (parametre d'un indicateur, comportement
d'une API tierce, preference du proprietaire non exprimee, etc.),
l'agent le dit explicitement et demande, plutot que de deviner une
valeur plausible et de l'implementer comme si elle etait confirmee.
Vaut pour le code, les specs, les cahiers des charges, et doit aussi
etre applique dans le prompt systeme du texte explicatif LLM lui-meme
(le moteur ne doit jamais deviner un chiffre absent du JSON "facts").

## Principe directeur : aucune donnee inventee

Deja pose dans le brief du projet, rappele ici car structurant pour tout
le code : distinguer toujours ce qui est calcule a partir d'une donnee
reelle de ce qui est une estimation ou une hypothese. Si une source de
donnees manque ou echoue, l'interface l'affiche explicitement ; le code
ne doit jamais substituer une valeur plausible a une donnee absente.
Le moteur deterministe (indicateurs, niveaux, scenarios) ne contient
aucun appel LLM ; le texte explicatif en LLM ne doit citer aucun chiffre
absent du JSON "facts" qui lui est fourni (controle automatique a
implementer avant toute mise en service du texte explicatif).

## Principe directeur : diagnostiquer un bug de bout en bout

La premiere cause trouvee n'est jamais consideree comme la cause unique
d'un incident. Un correctif doit verifier le parcours complet, depuis le
declencheur jusqu'au resultat visible, en passant par les appels
externes (sources de donnees), les calculs intermediaires et l'affichage.
Apres chaque hypothese corrigee, refaire le scenario reel ou son
equivalent automatise avant de presenter la PR.

## Principe directeur : la vue d'ensemble avant la ligne

Avant de modifier quoi que ce soit, verifier comment ce morceau de code
s'integre au reste de l'outil :

- Quel cahier des charges ce code sert-il ? Une modification doit rester
  coherente avec l'objectif et le perimetre de ce cahier, ou le cahier
  doit etre mis a jour en consequence.
- Ce code passe-t-il par les garde-fous deja en place (cache disque,
  distinction donnee/estimation, affichage de l'etat des sources) plutot
  que d'en recreer un nouveau ?
- Toute correction s'accompagne d'un test qui la verifie sur un cas
  concret, pas une supposition.

## Principe directeur : construire pour durer, pas pour depanner

Une solution transitoire ne se justifie que quand la contrainte elle-meme
est transitoire par nature, jamais par simple facilite de developpement.
Si une solution transitoire est malgre tout retenue (ex. une source de
donnees de secours en attendant de verifier une API officielle), le dire
explicitement dans le journal du cahier concerne : la contrainte qui
l'impose, et la condition de sortie.

## Principe directeur : rien ne part en production sans etre teste

- Tout developpement se fait sur une branche, ouverte en Pull Request a
  la fin de chaque phase, jamais un push direct sur `main` sans accord
  explicite du proprietaire.
- La CI doit passer au vert (tests du moteur deterministe) avant toute
  fusion, une fois mise en place.
- Toute nouvelle logique metier (pivots, zones, regime, scenarios)
  s'accompagne d'un test avec donnees figees.
- Aucun secret (cle API Anthropic, cle d'exchange si jamais necessaire)
  n'est commite : `.env` reste dans `.gitignore`, seul `.env.example` est
  versionne.

## Principe directeur : frugalite d'execution et de tokens

Lire et rechercher seulement les fichiers necessaires a la tache,
privilegier le code source et les commandes ciblees. Le resultat attendu
est une PR complete a relire et tester, pas une succession de validations
intermediaires.

## Principe directeur : une Pull Request est autoportee

Toute Pull Request doit etre comprehensible et verifiable par quelqu'un
qui n'a pas acces aux conversations precedentes. Le corps de la PR
contient, en francais :

1. **Le probleme de depart** : objectif de la phase ou de la
   fonctionnalite.
2. **La solution et son perimetre** : comportement avant et apres, ce qui
   est volontairement hors perimetre.
3. **Les criteres d'acceptation observables**, cas nominal et cas
   d'absence de donnee.
4. **Les preuves de verification** : commandes de test executees et
   resultat exact. Une verification non executee est nommee comme telle.
5. **La recette manuelle** : etapes pour tester sur mobile (via
   Tailscale), resultat attendu.

## Reperes pour situer tout changement

- Plan du projet et contraintes de deploiement : message d'origine du
  proprietaire (a terme, resume dans `docs/cahiers-des-charges/README.md`).
- Suivi d'avancement par phase : `docs/cahiers-des-charges/README.md`.
- Specs techniques validees par phase : `docs/specs-techniques/`.
- Regle sandbox donnees : jamais de cle d'exchange, lecture seule
  uniquement, voir le principe "aucune donnee inventee" ci-dessus.
