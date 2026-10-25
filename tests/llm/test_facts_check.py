from app.llm.facts_check import tous_les_nombres_sont_dans_facts

FACTS = {
    "prix_actuel": 80755.02,
    "rsi14": 43.82,
    "moyennes_mobiles": {"mm50": 81844.44, "mm200": 72941.69},
    "niveaux": [{"prix_haut": 97924.49, "prix_bas": 94789.08}],
}


def test_texte_conforme_passe():
    texte = "Le prix actuel est de 80 755,02, au-dessus de la MM200 à 72 941,69."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, FACTS)
    assert conforme
    assert manquants == []


def test_texte_avec_chiffre_invente_echoue():
    texte = "Le prix pourrait atteindre 123456,78 prochainement."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, FACTS)
    assert not conforme
    assert 123456.78 in manquants


def test_periode_indicateur_exemptee():
    texte = "Le RSI14 est à 43,82, la MM200 à 72 941,69."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, FACTS)
    assert conforme


def test_tolerance_arrondi():
    texte = "Le prix actuel est d'environ 80755."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, FACTS)
    assert conforme


def test_actif_a_tres_faible_valeur_unitaire_chiffre_reel_accepte():
    # Bug réel du 25/10/2026 (liste des actifs étendue à 22 cryptos,
    # dont SHIB ~0,000005) : l'arrondi à 2 décimales à l'extraction
    # réduisait tout nombre de cette échelle à "0.0", et le plancher de
    # tolérance fixe (0.01) aurait de toute façon accepté n'importe quel
    # petit chiffre comme "assez proche" de zéro.
    facts = {"prix_actuel": 0.0000052, "macd": {"ligne": -0.0000001}}
    texte = "Le prix est de 0,0000052 avec un MACD à -0,0000001."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, facts)
    assert conforme
    assert manquants == []


def test_actif_a_tres_faible_valeur_unitaire_chiffre_invente_rejete():
    facts = {"prix_actuel": 0.0000052}
    texte = "Le prix est de 0,0000091."  # jamais présent dans les facts
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, facts)
    assert not conforme
    assert 0.0000091 in manquants


def test_annee_dans_une_date_du_json_est_acceptee():
    # Bug réel en production (25/10/2026) : "2026" était rejeté comme
    # chiffre inventé car il n'apparaissait dans les facts qu'à
    # l'intérieur d'une date ("a_jour_le"), jamais comme nombre brut.
    facts = {**FACTS, "a_jour_le": "2026-10-25T13:47:12+00:00"}
    texte = "Les données sont à jour au 25 octobre 2026."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, facts)
    assert conforme
    assert manquants == []


def test_annee_absente_de_toute_date_du_json_reste_rejetee():
    texte = "Une analyse similaire avait été faite en 2019."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, FACTS)
    assert not conforme
    assert 2019.0 in manquants


def test_date_iso_ne_produit_pas_de_faux_nombres_negatifs():
    # Reproduction exacte du faux rejet en production (25/10/2026) : le
    # texte généré mentionnait la date de mise à jour, et le tiret de la
    # date ISO "2026-10-25" était lu comme un signe moins, produisant les
    # nombres -10 et -25 jamais présents dans les facts numériques.
    facts = {**FACTS, "a_jour_le": "2026-10-25T13:47:12+00:00"}
    texte = "Les données sont à jour au 2026-10-25."
    conforme, manquants = tous_les_nombres_sont_dans_facts(texte, facts)
    assert conforme
    assert manquants == []
