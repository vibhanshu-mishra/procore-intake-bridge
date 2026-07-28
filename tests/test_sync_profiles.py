from app.models.sync_profiles import SyncProfile


def test_sync_profile_belongs_to_connection(connection, sync_profile):
    assert sync_profile.connection_id == connection.id
    assert sync_profile.connection is connection
    assert sync_profile.procore_project_id == "project-1001"
    assert sync_profile.enabled is True


def test_profile_api_create_list_get_and_state(client, connection):
    response = client.post(
        "/sync-profiles",
        json={
            "connection_id": connection.id,
            "procore_project_id": "project-1001",
            "name": "Fixture polling",
            "polling_interval_minutes": 15,
            "mode": "mock",
        },
    )
    assert response.status_code == 201
    profile_id = response.json()["id"]
    assert client.get("/sync-profiles").json()[0]["id"] == profile_id
    assert client.get(f"/sync-profiles/{profile_id}").status_code == 200
    state = client.get(f"/sync-profiles/{profile_id}/state").json()
    assert state["due"] is True
    assert state["consecutive_failure_count"] == 0


def test_profile_patch_enabled_behavior(client, sync_profile):
    response = client.patch(
        f"/sync-profiles/{sync_profile.id}",
        json={"enabled": False, "polling_interval_minutes": 60},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["polling_interval_minutes"] == 60


def test_profile_project_must_be_allowlisted(client, connection):
    response = client.post(
        "/sync-profiles",
        json={
            "connection_id": connection.id,
            "procore_project_id": "synthetic-outside-allowlist",
            "name": "Rejected profile",
        },
    )
    assert response.status_code == 422


def test_profile_model_needs_no_live_project_access(db_session, connection):
    profile = SyncProfile(
        connection_id=connection.id,
        procore_project_id="placeholder-project",
        name="Local-only model",
        mode="mock",
    )
    db_session.add(profile)
    db_session.commit()
    assert profile.id is not None
