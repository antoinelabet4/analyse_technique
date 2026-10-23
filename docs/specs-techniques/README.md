# Specs techniques

Chaque fichier de ce dossier est la spec technique d'une fonctionnalite
deja decrite par un cahier des charges (`docs/cahiers-des-charges/`). Le
cahier dit le besoin ; la spec dit comment le code le realise, **et doit
etre validee par le proprietaire avant l'ecriture du code** (voir
`CLAUDE.md`, "pas de nouveau developpement sans cahier + spec technique
validee").

Nommage : `PN-nom-de-la-fonctionnalite.md`, ou `PN` reprend la phase
concernee (ex. `P1-moteur-indicateurs.md`, `P2-funding-open-interest.md`).

## Gabarit

```
# Spec technique : <nom>

Cahier associe : docs/cahiers-des-charges/PN-....md
Statut : brouillon | valide le JJ/MM/AAAA par le proprietaire

## Besoin
(rappel court du besoin couvert, sans le reexpliquer en entier)

## Donnees
(sources utilisees, format, cache, ce qui est affiche comme calcule vs
estimation, comportement si la source manque ou echoue)

## Contrat d'API / de fonction
(signature, entrees, sorties, cas d'erreur)

## Garde-fous
(aucune donnee inventee, distinction donnee/estimation, limite d'appels
LLM, ce qui rend cette fonctionnalite sure -- voir CLAUDE.md)

## Plan de test
(quels tests unitaires couvriront cette fonctionnalite, avec quelles
donnees figees, quels cas concrets)
```
