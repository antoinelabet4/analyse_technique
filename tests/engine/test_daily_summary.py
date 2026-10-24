from app.engine import daily_summary as daily_summary_module

BTC_FACTS = {
    "prix_actuel": 80000.0,
    "regime": {"prix_vs_mm_longue": "au_dessus", "pente_mm_longue": "haussiere", "structure": "hausse"},
    "onchain": {"disponible": True, "date_donnee": "2026-10-17", "sopr": 1.0, "mvrv": 1.5, "mvrv_zscore": 0.9, "puell_multiple": 1.0},
    "cycle": {"disponible": True, "position": "dans", "borne_basse_actuelle": 50000.0, "borne_haute_actuelle": 120000.0, "tendance_actuelle": 80000.0},
    "scenarios": [{"type": "haussier", "condition_cloture": "x", "cible": 90000.0}],
    "force_relative_btc": None,
}

ALT_FACTS = {
    "prix_actuel": 2000.0,
    "force_relative_btc": {"tendance": "hausse"},
}


def test_resume_contient_btc_et_tous_les_alts(monkeypatch):
    def fake_build_facts(asset, timeframe):
        return BTC_FACTS if asset == "BTC" else ALT_FACTS

    monkeypatch.setattr(daily_summary_module, "build_facts", fake_build_facts)
    resume = daily_summary_module.construire_resume_quotidien()
    assert "BTC" in resume
    assert "ETH" in resume and "XRP" in resume and "TAO" in resume and "RENDER" in resume
    assert "SOPR" in resume
    assert "Canal de cycle" in resume
    assert "pas un conseil financier" in resume


def test_resume_gere_un_alt_en_echec(monkeypatch):
    def fake_build_facts(asset, timeframe):
        if asset == "BTC":
            return BTC_FACTS
        if asset == "ETH":
            raise RuntimeError("source indisponible")
        return ALT_FACTS

    monkeypatch.setattr(daily_summary_module, "build_facts", fake_build_facts)
    resume = daily_summary_module.construire_resume_quotidien()
    assert "ETH : indisponible aujourd'hui" in resume


def test_resume_signale_onchain_et_cycle_indisponibles(monkeypatch):
    facts_sans_onchain = {**BTC_FACTS, "onchain": {"disponible": False}, "cycle": {"disponible": False}}

    def fake_build_facts(asset, timeframe):
        return facts_sans_onchain if asset == "BTC" else ALT_FACTS

    monkeypatch.setattr(daily_summary_module, "build_facts", fake_build_facts)
    resume = daily_summary_module.construire_resume_quotidien()
    assert "On-chain : indisponible aujourd'hui" in resume
    assert "Canal de cycle : indisponible aujourd'hui" in resume
