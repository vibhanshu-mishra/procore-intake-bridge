from fastapi import HTTPException

from app.main import app
from app.routers.admin import admin_guard

JSON_LIST_ROUTES = (
    "/admin/api/connections",
    "/admin/api/sync-profiles",
    "/admin/api/sync-runs",
    "/admin/api/intake-records",
    "/admin/api/attachments",
    "/admin/api/webhook-events",
    "/admin/api/onboarding-packets",
)


def test_admin_json_empty_states_and_safety(client):
    overview = client.get("/admin/api/overview")
    assert overview.status_code == 200
    assert all(card["count"] == 0 for card in overview.json()["count_cards"])
    assert overview.json()["safety"]["read_only"] is True
    assert overview.json()["safety"]["procore_writes"] is False
    assert client.get("/admin/api/safety").status_code == 200
    for route in JSON_LIST_ROUTES:
        response = client.get(route)
        assert response.status_code == 200
        assert response.json() == []


def test_admin_json_uses_safe_connection_and_profile_projections(
    client, connection, sync_profile
):
    connection_data = client.get("/admin/api/connections").json()[0]
    profile_data = client.get("/admin/api/sync-profiles").json()[0]
    serialized = f"{connection_data} {profile_data}"
    assert connection_data["company_id_masked"] == "com***est"
    assert profile_data["project_id_masked"] == "pro***001"
    assert connection_data["display_name"].startswith("Connection #")
    assert "Synthetic contractor" not in serialized
    assert "secret/test-placeholder" not in serialized
    assert "project-1001" not in serialized


def test_admin_guard_controls_all_admin_routes(client):
    def disabled():
        raise HTTPException(status_code=404, detail="Admin dashboard is disabled.")

    app.dependency_overrides[admin_guard] = disabled
    assert client.get("/admin").status_code == 404
    assert client.get("/admin/api/overview").status_code == 404
    app.dependency_overrides.pop(admin_guard)


def test_admin_list_limit_is_capped_at_one_hundred(client, db_session):
    from app.models.connections import DMSAConnection

    db_session.add_all(
        [
            DMSAConnection(
                name=f"Synthetic {index}",
                procore_company_id=f"company-{index}",
                permitted_project_ids=[],
                enabled_tools=[],
                secret_name=f"secret-{index}",
            )
            for index in range(105)
        ]
    )
    db_session.commit()
    response = client.get("/admin/api/connections?limit=1000")
    assert response.status_code == 200
    assert len(response.json()) == 100
