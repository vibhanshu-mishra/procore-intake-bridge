def test_deployment_routes_are_sanitized(client):
    readiness = client.get("/deployment/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["environment"] == "local"
    assert client.get("/deployment/safety").status_code == 200
    summary = client.get("/deployment/config-summary")
    assert summary.status_code == 200
    assert "secret_name" not in summary.text


def test_ready_includes_database_and_deployment_summary(client):
    payload = client.get("/ready").json()
    assert payload["database_connected"] is True
    assert payload["deployment"]["environment"] == "local"
