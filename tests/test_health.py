from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_index_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_manifest_served_at_root_and_valid_json():
    res = client.get("/manifest.json")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Analyse technique crypto"
    assert data["scope"] == "/"
    assert len(data["icons"]) >= 2


def test_service_worker_served_at_root_for_full_scope():
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]


def test_icons_are_served():
    for nom in ["icon-192.png", "icon-512.png", "apple-touch-icon.png"]:
        res = client.get(f"/static/icons/{nom}")
        assert res.status_code == 200, nom


def test_html_css_js_manifest_et_sw_ne_sont_jamais_mis_en_cache():
    # Bug trouvé le 25/10/2026 : sans Cache-Control explicite, Safari iOS
    # en PWA installée pouvait continuer à servir une version périmée de
    # ces fichiers après un redéploiement (un correctif CSS pourtant en
    # production restait invisible sur l'appareil).
    for chemin in ["/", "/manifest.json", "/sw.js", "/static/style.css", "/static/app.js"]:
        res = client.get(chemin)
        assert res.headers.get("cache-control") == "no-cache", chemin
