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
