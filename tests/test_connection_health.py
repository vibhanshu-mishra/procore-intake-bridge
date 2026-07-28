from app.services.connection_health import check_connection_health


def test_health_check_is_deterministic_and_mocked(connection):
    first = check_connection_health(connection)
    second = check_connection_health(connection)
    assert first == second
    assert first.token_check == "mock_valid"
    assert "No live Procore request was made." in first.findings


def test_health_route(client, connection):
    response = client.post(f"/connections/{connection.id}/health-check")
    assert response.status_code == 200
    assert response.json()["rfi_access"] == "mock_read_only"
