from app.config import Settings
from app.services import procore_client
from app.services.connection_health import check_connection_health


def test_health_check_is_deterministic_and_mocked(connection):
    first = check_connection_health(connection)
    second = check_connection_health(connection)
    assert first == second
    assert first.mode == "mock"
    assert first.token_check == "mock_valid"
    assert "No live Procore request was made." in first.findings


def test_health_route(client, connection):
    response = client.post(f"/connections/{connection.id}/health-check")
    assert response.status_code == 200
    assert response.json()["rfi_access"] == "mock_read_only"


def test_live_health_disabled_is_safe(client, connection):
    response = client.post(f"/connections/{connection.id}/health-check?mode=live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "live_gated"
    assert payload["live_mode_enabled"] is False
    assert payload["secret_resolved"] is False
    assert payload["project_access"] == {"project-1001": "not_checked"}


def test_live_health_enabled_uses_mocked_adapter(monkeypatch, connection):
    connection.client_id_ref = "demo_client_id"
    settings = Settings(_env_file=None, procore_live_mode_enabled=True)

    class Provider:
        def get_secret(self, _name):
            return "synthetic"

    fake_client = object()
    monkeypatch.setattr(
        procore_client,
        "build_pyprocore_client_for_connection",
        lambda *_args: fake_client,
    )
    monkeypatch.setattr(procore_client, "check_project_access", lambda *_args: True)
    monkeypatch.setattr(procore_client, "check_rfi_access", lambda *_args: True)
    monkeypatch.setattr(procore_client, "check_submittal_access", lambda *_args: True)

    result = check_connection_health(
        connection,
        mode="live",
        settings=settings,
        secret_provider=Provider(),
    )
    assert result.live_mode_enabled is True
    assert result.secret_resolved is True
    assert result.pyprocore_client_buildable is True
    assert result.project_access == {"project-1001": "accessible"}
    assert result.rfi_access == "readable"
