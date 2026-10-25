from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm import analysis as analysis_module
from app.llm.analysis import DebitDepasse, PlafondAtteint, TexteNonFiable, _facts_pour_prompt, generer_analyse

TEXTE_VALIDE = {
    "verdict": "attendre",
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
    facts["rsi_serie"] = [{"time": "2026-01-01", "valeur": 55.0}]
    facts["macd"] = {"ligne": 1.0, "signal": 0.5, "histogramme": 0.5, "serie": [{"time": "2026-01-01", "ligne": 1.0, "signal": 0.5, "histogramme": 0.5}]}

    reduit = _facts_pour_prompt(facts)

    assert "candles" not in reduit
    assert "moyennes_mobiles_serie" not in reduit
    assert "rsi_serie" not in reduit
    assert "nuage_serie" not in reduit["ichimoku"]
    assert "serie" not in reduit["macd"]
    # Les valeurs résumées, elles, restent présentes pour le texte explicatif.
    assert reduit["ichimoku"]["tenkan"] == 100.0
    assert reduit["macd"]["ligne"] == 1.0
    assert reduit["prix_actuel"] == facts["prix_actuel"]
    assert reduit["moyennes_mobiles"] == facts["moyennes_mobiles"]
    # La fonction ne modifie pas le dict d'origine (toujours utilisé pour
    # la clé de cache et le contrôle des chiffres).
    assert "candles" in facts


def test_premier_appel_interroge_le_llm_et_met_en_cache(tmp_path: Path, monkeypatch):
    appels = []
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: (appels.append(1), TEXTE_VALIDE)[1])

    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=tmp_path / "cache.db")

    assert resultat.source_cache is False
    assert resultat.texte == TEXTE_VALIDE
    assert len(appels) == 1


def test_deuxieme_appel_meme_bougie_sert_le_cache_sans_rappeler_le_llm(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: (appels.append(1), TEXTE_VALIDE)[1])

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)

    assert resultat.source_cache is True
    assert len(appels) == 1  # pas de deuxième appel LLM


def test_nouvelle_bougie_invalide_le_cache(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []
    monkeypatch.setattr(analysis_module, "DEBIT_MINIMUM_SECONDES", 0)
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: (appels.append(1), TEXTE_VALIDE)[1])

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
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: TEXTE_VALIDE)

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    generer_analyse("ETH", "1d", _facts(), cache_path=cache_path)
    with pytest.raises(PlafondAtteint):
        generer_analyse("XRP", "1d", _facts(), cache_path=cache_path)


def test_debit_minimum_entre_deux_appels(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: TEXTE_VALIDE)

    generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)
    with pytest.raises(DebitDepasse):
        generer_analyse("ETH", "1d", _facts(), cache_path=cache_path)


def test_texte_non_fiable_apres_deux_echecs_du_controle(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    texte_invente = {**TEXTE_VALIDE, "tendance": "Le prix pourrait grimper à 999999,99."}
    monkeypatch.setattr(analysis_module, "_appeler_llm", lambda facts, modele, **kwargs: texte_invente)

    with pytest.raises(TexteNonFiable):
        generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)


def test_le_reessai_recoit_les_chiffres_rejetes(tmp_path: Path, monkeypatch):
    # Bug du 25/10/2026 : le deuxième essai utilisait le même prompt que
    # le premier, sans jamais dire au modèle quels chiffres avaient été
    # rejetés, ce qui le laissait répéter la même erreur.
    cache_path = tmp_path / "cache.db"
    appels_chiffres_a_eviter = []

    def faux_appel(facts, modele, chiffres_a_eviter=None):
        appels_chiffres_a_eviter.append(chiffres_a_eviter)
        if chiffres_a_eviter is None:
            return {**TEXTE_VALIDE, "tendance": "Le prix pourrait grimper à 999999,99."}
        return TEXTE_VALIDE

    monkeypatch.setattr(analysis_module, "_appeler_llm", faux_appel)

    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)

    assert resultat.texte == TEXTE_VALIDE
    assert appels_chiffres_a_eviter[0] is None
    assert appels_chiffres_a_eviter[1] == [999999.99]


class _BlocTexte:
    def __init__(self, texte: str) -> None:
        self.type = "text"
        self.text = texte


class _MessageFactice:
    def __init__(self, texte: str, stop_reason: str) -> None:
        self.content = [_BlocTexte(texte)] if texte else []
        self.stop_reason = stop_reason


def test_appeler_llm_leve_texte_non_fiable_si_reponse_tronquee(monkeypatch):
    # Bug réel du 25/10/2026 (production) : une fois la clé API configurée,
    # le premier appel réel a échoué avec une réponse coupée en plein
    # milieu d'une chaîne JSON (budget de tokens trop court), et une
    # JSONDecodeError peu parlante remontait jusqu'au client sans qu'on
    # sache si c'était une panne de la clé, du modèle ou du réseau.
    reponse_tronquee = '{"tendance": "Prix à 100 au-dessus de la MM200'
    message_factice = _MessageFactice(reponse_tronquee, stop_reason="max_tokens")
    client_factice = type("ClientFactice", (), {"messages": type("Messages", (), {"create": staticmethod(lambda **kw: message_factice)})()})()
    monkeypatch.setattr(analysis_module.anthropic, "Anthropic", lambda: client_factice)

    with pytest.raises(TexteNonFiable, match="max_tokens"):
        analysis_module._appeler_llm(_facts(), "claude-sonnet-5-5")


def test_appeler_llm_leve_texte_non_fiable_si_reponse_vide(monkeypatch):
    # Deuxième panne réelle observée (25/10/2026) : la réponse ne contenait
    # aucun bloc de texte du tout.
    message_factice = _MessageFactice("", stop_reason="end_turn")
    client_factice = type("ClientFactice", (), {"messages": type("Messages", (), {"create": staticmethod(lambda **kw: message_factice)})()})()
    monkeypatch.setattr(analysis_module.anthropic, "Anthropic", lambda: client_factice)

    with pytest.raises(TexteNonFiable):
        analysis_module._appeler_llm(_facts(), "claude-sonnet-5-5")


def _client_factice_avec_json(payload: dict):
    texte = json.dumps(payload, ensure_ascii=False)
    message_factice = _MessageFactice(texte, stop_reason="end_turn")
    return type("ClientFactice", (), {"messages": type("Messages", (), {"create": staticmethod(lambda **kw: message_factice)})()})()


def test_appeler_llm_leve_texte_non_fiable_si_verdict_absent(monkeypatch):
    sans_verdict = {k: v for k, v in TEXTE_VALIDE.items() if k != "verdict"}
    monkeypatch.setattr(analysis_module.anthropic, "Anthropic", lambda: _client_factice_avec_json(sans_verdict))

    with pytest.raises(TexteNonFiable, match="[Vv]erdict"):
        analysis_module._appeler_llm(_facts(), "claude-sonnet-5-5")


def test_appeler_llm_leve_texte_non_fiable_si_verdict_hors_liste(monkeypatch):
    # Demande explicite du propriétaire (25/10/2026) : le LLM doit trancher
    # avec un verdict achat/vente/attente, mais ce jugement n'étant pas un
    # chiffre vérifiable contre les facts, on contraint au moins sa forme
    # à l'une des trois valeurs exactes attendues.
    verdict_invente = {**TEXTE_VALIDE, "verdict": "achat massif"}
    monkeypatch.setattr(analysis_module.anthropic, "Anthropic", lambda: _client_factice_avec_json(verdict_invente))

    with pytest.raises(TexteNonFiable, match="[Vv]erdict"):
        analysis_module._appeler_llm(_facts(), "claude-sonnet-5-5")


def test_appeler_llm_accepte_les_trois_verdicts_valides(monkeypatch):
    for verdict in ("acheter", "vendre", "attendre"):
        monkeypatch.setattr(analysis_module.anthropic, "Anthropic", lambda: _client_factice_avec_json({**TEXTE_VALIDE, "verdict": verdict}))
        resultat = analysis_module._appeler_llm(_facts(), "claude-sonnet-5-5")
        assert resultat["verdict"] == verdict


def test_reponse_tronquee_est_reessayee_une_fois(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "cache.db"
    appels = []

    def appel_qui_echoue_puis_reussit(facts, modele):
        appels.append(1)
        if len(appels) == 1:
            raise TexteNonFiable("Réponse LLM non interprétable en JSON (stop_reason=max_tokens) : simulée")
        return TEXTE_VALIDE

    monkeypatch.setattr(analysis_module, "_appeler_llm", appel_qui_echoue_puis_reussit)

    resultat = generer_analyse("BTC", "1d", _facts(), cache_path=cache_path)

    assert resultat.texte == TEXTE_VALIDE
    assert len(appels) == 2
