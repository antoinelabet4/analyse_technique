from app.engine.facts import _nombre_ou_none


def test_nombre_normal_arrondi_a_six_decimales():
    assert _nombre_ou_none(80755.123456789) == 80755.123457


def test_nombre_tres_petit_garde_plus_de_decimales():
    # Bug réel du 25/10/2026 (liste des actifs étendue à 22 cryptos,
    # dont SHIB ~0,000005) : l'arrondi fixe à 6 décimales réduisait un
    # MACD de cette échelle à 0.0, perdant toute précision utile.
    assert _nombre_ou_none(0.0000000123456) == 0.000000012346


def test_zero_reste_zero():
    assert _nombre_ou_none(0.0) == 0.0


def test_none_reste_none():
    assert _nombre_ou_none(None) is None
