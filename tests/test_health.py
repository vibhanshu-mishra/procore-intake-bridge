def test_app_imports():
    from app.main import app

    assert app.title == "Procore Intake Bridge"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "fixture"}
    assert client.get("/ready").status_code == 200


def test_safety_explains_no_writes(client):
    payload = client.get("/safety").json()
    assert payload["read_only"] is True
    assert payload["procore_writes"] is False
    assert payload["live_procore_calls"] is False
