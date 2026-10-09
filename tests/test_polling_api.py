from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models.intake_records import IntakeRecord
from app.services import polling_worker

FIXTURE_RUN_NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


class _FrozenPollingDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXTURE_RUN_NOW.replace(tzinfo=None)
        return FIXTURE_RUN_NOW.astimezone(tz)


def test_profile_dry_run_does_not_write(client, db_session, sync_profile):
    response = client.post(f"/sync-profiles/{sync_profile.id}/dry-run")
    assert response.status_code == 200
    assert response.json()["status"] == "dry_run"
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 0
    db_session.refresh(sync_profile)
    assert sync_profile.last_watermark_at is None


def test_profile_run_once_writes_fixture_records(
    client, db_session, sync_profile, monkeypatch
):
    monkeypatch.setattr(polling_worker, "datetime", _FrozenPollingDateTime)

    response = client.post(f"/sync-profiles/{sync_profile.id}/run-once")
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["record_count"] == 2
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 2
    db_session.refresh(sync_profile)
    watermark = sync_profile.last_watermark_at
    assert watermark is not None
    assert watermark.replace(tzinfo=UTC) == FIXTURE_RUN_NOW

    repeated = client.post(f"/sync-profiles/{sync_profile.id}/run-once")
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "succeeded"
    assert repeated.json()["record_count"] == 0
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 2


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
