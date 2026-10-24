from __future__ import annotations

from pathlib import Path

import pytest

from app.llm import analysis as analysis_module
from app.llm.analysis import DebitDepasse, PlafondAtteint, TexteNonFiable, _facts_pour_prompt, generer_analyse

TEXTE_VALIDE = {
    "tendance": "Prix à 100 au-dessus de la MM200 à 90.",
    "niveaux": "Résistance à 110.",
    "scenarios": "Haussier si clôture au-dessus de 110.",
    "ce_qui_changerait": "Une clôture sous 90.",
    "risques": "Volatilité (ATR à 2).",
}


def _facts():
    return {
        "candles": [{"time": "2026-01-01"}, {"time": "2026-01-02"}],
        "prix_actuel": 100.0,
        "moyennes_mobiles": {"mm200": 90.0},
        "moyennes_mobiles_serie": {"mm200": [{"time": "2026-01-01", "valeur": 88.0}]},
        "niveaux": [{"prix_haut": 110.0, "prix_bas": 108.0}],
        "atr14": 2.0,
    }


def test_facts_pour_prompt_retire_les_series_volumineuses():
    facts = _facts()
    facts["ichimoku"] = {"tenkan": 100.0, "nuage_serie": [{"time": "2026-01-01", "senkou_a": 1.0, "senkou_b": 2.0}]}

    reduit = _facts_pour_prompt(facts)

    assert "candles" not in reduit
    assert "moyennes_mobiles_serie" not in reduit
    assert "nuage_serie" not in reduit["ichimoku"]
    # Les valeurs résumées, elles, restent présentes pour le texte explicatif.
    assert reduit["ichimoku"]["tenkan"] == 100.0
    assert reduit["prix_actuel"] == facts["prix_actuel"]
    assert reduit["moyennes_mobiles"] == facts["moyennes_mobiles"]
    # La fonction ne modifie pas le dict d'origine (toujours utilisé pour
    # la clé de cache et le contrôle des chiffres).
    assert "candles" in facts


def test_premier_appel_interroge_le_llm_et_met_en_cache(tmp_path: Path, monkeypatch):
    appels = []
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: (appels.append(1), TEXTE_VALIDE)[1])

    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=tmp_path / "cache.db")

    assert resultat.source_cache is False
    assert resultat.texte == TEXTE_VALIDE
    assert len(appels) == 1


def test_deuxieme_appel_meme_bougie_sert_le_cache_sans_rappeler_le_llm(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: (appels.append(1), TEXTE_VALIDE)[1])

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)

    assert resultat.source_cache is True
    assert len(appels) == 1  # pas de deuxième appel LLM


def test_nouvelle_bougie_invalide_le_cache(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    monkeypatch.setattr(analysis_module, "DEBIT_MINIMUM_SECONDES", 0)
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: (appels.append(1), TEXTE_VALIDE)[1])

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    facts_nouvelle_bougie = _facts()
    facts_nouvelle_bougie["candles"].append({"time": "2026-01-03"})
    resultat = generer_analyse("BTC", "1d", facts_nouvelle_bougie, cache_path=cache_path)

    assert resultat.source_cache is False
    assert len(appels) == 2


def test_plafond_quotidien_atteint(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(analysis_module, "PLAFOND_QUOTIDIEN", 2)
    monkeypatch.setattr(analysis_module, "DEBIT_MINIMUM_SECONDES", 0)
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: TEXTE_VALIDE)

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    generer_analyse("ETH", "1d", _facts(), cache_path=cache_path)
    with pytest.raises(PlafondAtteint):
        generer_analyse("XRP", "1d", _facts(), cache_path=cache_path)


def test_debit_minimum_entre_deux_appels(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: TEXTE_VALIDE)

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    with pytest.raises(DebitDepasse):
        generer_analyse("ETH", "1d", _facts(), cache_path=cache_path)


def test_texte_non_fiable_apres_deux_echecs_du_controle(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    texte_invente = {**TEXTE_VALIDE, "tendance": "Le prix pourrait grimper à 999999,99."}
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele: texte_invente)

    with pytest.raises(TexteNonFiable):
        generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
