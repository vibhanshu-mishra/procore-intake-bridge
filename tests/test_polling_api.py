from sqlalchemy import func, select

from app.models.intake_records import IntakeRecord


def test_profile_dry_run_does_not_write(client, db_session, sync_profile):
    response = client.post(f"/sync-profiles/{sync_profile.id}/dry-run")
    assert response.status_code == 200
    assert response.json()["status"] == "dry_run"
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 0
    db_session.refresh(sync_profile)
    assert sync_profile.last_watermark_at is None


def test_profile_run_once_writes_fixture_records(client, db_session, sync_profile):
    response = client.post(f"/sync-profiles/{sync_profile.id}/run-once")
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 2
    db_session.refresh(sync_profile)
    assert sync_profile.last_watermark_at is not None


def test_disabled_profile_requires_force(client, sync_profile):
    client.patch(f"/sync-profiles/{sync_profile.id}", json={"enabled": False})
    blocked = client.post(f"/sync-profiles/{sync_profile.id}/run-once")
    assert blocked.status_code == 409
    forced = client.post(f"/sync-profiles/{sync_profile.id}/run-once?force=true")
    assert forced.status_code == 200
    assert forced.json()["status"] == "succeeded"


def test_locked_profile_returns_conflict(client, db_session, sync_profile):
    from datetime import UTC, datetime

    sync_profile.locked_at = datetime.now(UTC)
    sync_profile.lock_owner = "other-worker"
    db_session.commit()
    response = client.post(f"/sync-profiles/{sync_profile.id}/dry-run")
    assert response.status_code == 409
    assert "active lock" in response.json()["detail"]


def test_polling_run_once_summarizes_due_profiles(client, sync_profile):
    response = client.post("/polling/run-once")
    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["due_profiles_count"] == 1
    assert payload["succeeded_count"] == 1


def test_live_mode_disabled_prevents_live_polling(client, sync_profile):
    response = client.post(
        f"/sync-profiles/{sync_profile.id}/dry-run?mode=live"
    )
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]
