# UI — RSI et MACD en sous-graphiques

## Objectif

Demande explicite du propriétaire : afficher le RSI et le MACD comme de
vrais sous-graphiques sous le graphique principal (comme sur une
application boursière), pas seulement comme une valeur numérique dans le
résumé texte.

## Périmètre

- Inclus :
  - Calcul du MACD (`app/engine/indicators.py`), absent jusqu'ici du
    moteur : ligne (EMA12 - EMA26), signal (EMA9 de la ligne),
    histogramme (ligne - signal). Réglages classiques 12/26/9, même point
    ouvert que pour l'Ichimoku (aucun paramétrage spécifique à la méthode
    de Vincent Ganne confirmé).
  - Séries complètes RSI14 et MACD exposées dans le JSON "facts"
    (`rsi_serie`, `macd.serie`), en plus des valeurs actuelles déjà
    présentes.
  - Deux sous-graphiques (panes Lightweight Charts) sous le graphique de
    prix : RSI avec repères 30/70, MACD avec ligne, signal et histogramme
    coloré (vert/rouge selon le signe).
  - Cases à cocher dédiées dans le menu "Indicateurs" pour masquer/
    afficher chaque sous-graphique indépendamment, mêmes conventions que
    les indicateurs existants (persisté en localStorage).
  - Retrait des deux séries complètes (`rsi_serie`, `macd.serie`) du JSON
    envoyé au texte explicatif LLM, comme pour les bougies/le nuage/les
    moyennes mobiles : les valeurs résumées (RSI14, MACD ligne/signal/
    histogramme actuels) restent disponibles pour le texte.
- Non inclus : réglage des périodes RSI/MACD par l'utilisateur (valeurs
  fixes, comme les autres indicateurs) ; redimensionnement dynamique des
  sous-graphiques quand ils sont masqués (l'espace reste réservé, pas
  d'optimisation de mise en page pour ce cas).

## État d'avancement

**Fait — 25/10/2026.**

## Critères de validation

- [x] Le RSI s'affiche comme une courbe sous le graphique de prix, avec
      des repères à 30 et 70.
- [x] Le MACD s'affiche comme un deuxième sous-graphique (ligne, signal,
      histogramme coloré).
- [x] Décocher "RSI (14)" ou "MACD (12/26/9)" masque le sous-graphique
      correspondant sans recharger les données.
- [x] Changer d'actif ou de timeframe met à jour les deux sous-graphiques
      sans erreur JS ni donnée résiduelle de l'actif précédent.
- [x] Le mode plein écran affiche toujours les deux sous-graphiques.
- [x] Les séries complètes RSI/MACD ne sont pas envoyées au LLM (coût
      maîtrisé), seules les valeurs actuelles le sont.

## Journal

- **25/10/2026** — `macd()` ajouté à `app/engine/indicators.py` (3 tests
  avec données figées : ligne = différence des EMA de référence,
  histogramme = ligne - signal, NaN avant assez d'historique).
  `build_facts` expose `rsi_serie` et `macd` (valeurs actuelles +
  `serie`). Côté client, deux sous-graphiques Lightweight Charts v5 (API
  panes : `chart.addSeries(Type, options, paneIndex)`, confirmée présente
  dans la version vendue 5.2.1), créés une seule fois (contrairement aux
  moyennes mobiles, leur nombre ne varie jamais avec le timeframe), avec
  une hauteur fixe de 90px chacun ; le graphique de prix principal passe
  de 48vh à 62vh pour leur faire de la place. Vérifié par Playwright avec
  données réelles Binance (BTC et ETH, 1D et 1W) : rendu correct des deux
  sous-graphiques, masquage/affichage via les cases à cocher, changement
  d'actif/timeframe et mode plein écran sans erreur JS. 128 tests backend
  passent (125 existants + 3 nouveaux sur `macd()`, assertions
  supplémentaires sur `build_facts` et `_facts_pour_prompt`).
