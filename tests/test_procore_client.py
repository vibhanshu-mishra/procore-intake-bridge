import pytest

from app.config import Settings
from app.services import procore_client


class FakeProvider:
    def get_secret(self, name):
        return f"synthetic-for-{name}"


def test_live_mode_disabled_blocks_builder(monkeypatch, connection):
    connection.client_id_ref = "client_id"
    called = False

    def forbidden(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(procore_client, "_instantiate_pyprocore_client", forbidden)
    with pytest.raises(procore_client.LiveProcoreDisabledError):
        procore_client.build_pyprocore_client_for_connection(
            connection,
            Settings(_env_file=None, procore_live_mode_enabled=False),
            FakeProvider(),
        )
    assert called is False


def test_live_mode_enabled_uses_isolated_mocked_builder(monkeypatch, connection):
    connection.client_id_ref = "client_id"
    sentinel = object()
    captured = {}

    def fake_builder(received_connection, credentials, received_settings):
        captured["connection"] = received_connection
        captured["client_id"] = credentials.client_id.get_secret_value()
        captured["client_secret"] = credentials.client_secret.get_secret_value()
        captured["settings"] = received_settings
        return sentinel

    monkeypatch.setattr(
        procore_client,
        "_instantiate_pyprocore_client",
        fake_builder,
    )
    settings = Settings(_env_file=None, procore_live_mode_enabled=True)
    result = procore_client.build_pyprocore_client_for_connection(
        connection, settings, FakeProvider()
    )
    assert result is sentinel
    assert captured["connection"] is connection
    assert captured["settings"] is settings
    assert captured["client_id"] == "synthetic-for-client_id"
    assert captured["client_secret"] == "synthetic-for-secret/test-placeholder"
