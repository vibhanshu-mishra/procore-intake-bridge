import json
from pathlib import Path

from sqlalchemy import func, select

from app.config import Settings
from app.models.onboarding_packets import OnboardingPacket
from app.services import onboarding_packet


def payload(**overrides):
    values = {
        "packet_name": "Example GC Packet",
        "recipient_company_name": "Example GC Company",
        "requester_company_name": "Example Engineering Firm",
        "requested_project_ids": ["111111"],
        "app_version_key_ref": "APP_VERSION_KEY_PLACEHOLDER",
    }
    values.update(overrides)
    return values


def packet_count(session):
    return session.scalar(select(func.count()).select_from(OnboardingPacket))


def test_default_permissions_route(client):
    response = client.get("/onboarding/default-permissions")
    assert response.status_code == 200
    assert any(
        item["tool"] == "RFIs" and item["access"] == "Read Only"
        for item in response.json()
    )


def test_preview_does_not_persist(client, db_session):
    response = client.post("/onboarding/preview", json=payload())
    assert response.status_code == 200
    assert response.json()["persisted"] is False
    assert response.json()["markdown"].startswith("# Example GC Packet")
    assert packet_count(db_session) == 0


def test_generate_persists_list_and_get(client, db_session):
    generated = client.post("/onboarding/generate", json=payload())
    assert generated.status_code == 200
    packet_id = generated.json()["packet_id"]
    assert generated.json()["persisted"] is True
    assert packet_count(db_session) == 1
    assert client.get("/onboarding-packets").json()[0]["id"] == packet_id
    detail = client.get(f"/onboarding-packets/{packet_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "generated"


def test_connection_packet_uses_local_permitted_projects(
    client, db_session, connection, sync_profile
):
    response = client.post(
        f"/connections/{connection.id}/onboarding-packet",
        json=payload(requested_project_ids=[]),
    )
    assert response.status_code == 200
    packet = db_session.scalar(select(OnboardingPacket))
    assert packet.connection_id == connection.id
    assert packet.requested_project_ids_json == ["project-1001"]
    assert set(packet.requested_tools_json) == {"rfis", "submittals"}
    assert "project-1001" in packet.generated_markdown


def test_connection_packet_needs_no_body(client, connection):
    response = client.post(
        f"/connections/{connection.id}/onboarding-packet"
    )
    assert response.status_code == 200
    assert "GC_OWNER_COMPANY_PLACEHOLDER" in response.json()["markdown"]


def test_local_export_is_sanitized_and_gitignored(
    monkeypatch, tmp_path, client
):
    config = Settings(_env_file=None, packet_output_root=tmp_path)
    monkeypatch.setattr(onboarding_packet, "get_settings", lambda: config)
    generated = client.post(
        "/onboarding/generate",
        json=payload(packet_name="../../ Private Packet"),
    ).json()
    response = client.post(
        f"/onboarding-packets/{generated['packet_id']}/export-local"
    )
    assert response.status_code == 200
    result = response.json()
    assert not result["markdown_path"].startswith("/")
    assert ".." not in Path(result["markdown_path"]).parts
    assert (tmp_path / result["markdown_path"]).exists()
    assert (tmp_path / result["json_path"]).exists()


def test_api_ignores_secret_shaped_extra_fields(client):
    request = payload()
    request["client_secret"] = "must-not-appear"
    request["access_token"] = "must-not-appear-either"
    response = client.post("/onboarding/preview", json=request)
    serialized = json.dumps(response.json())
    assert response.status_code == 200
    assert "must-not-appear" not in serialized
