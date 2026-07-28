from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.models.sync_profiles import SyncProfile
from app.services import polling_worker

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_find_due_profiles_skips_not_due(db_session, connection, sync_profile):
    future = SyncProfile(
        connection_id=connection.id,
        procore_project_id="project-future",
        name="Future",
        next_run_at=NOW + timedelta(minutes=1),
    )
    db_session.add(future)
    db_session.commit()
    assert polling_worker.find_due_sync_profiles(db_session, NOW) == [sync_profile]


def test_lock_overlap_stale_recovery_and_release(db_session, sync_profile):
    config = settings(sync_lock_timeout_minutes=30)
    assert polling_worker.acquire_sync_lock(
        db_session, sync_profile, "worker-one", NOW, config
    )
    assert sync_profile.lock_owner == "worker-one"
    assert not polling_worker.acquire_sync_lock(
        db_session, sync_profile, "worker-two", NOW + timedelta(minutes=5), config
    )
    assert polling_worker.acquire_sync_lock(
        db_session, sync_profile, "worker-two", NOW + timedelta(minutes=31), config
    )
    assert sync_profile.lock_owner == "worker-two"
    polling_worker.release_sync_lock(db_session, sync_profile)
    assert sync_profile.locked_at is None
    assert sync_profile.lock_owner is None


def test_calculate_next_run():
    assert polling_worker.calculate_next_run_at(NOW, 30) == NOW + timedelta(minutes=30)


def test_success_updates_state_and_watermark(db_session, sync_profile):
    result = polling_worker.run_sync_profile_once(
        db_session,
        sync_profile.id,
        now=NOW,
        settings=settings(max_sync_lookback_days=30),
    )
    db_session.refresh(sync_profile)
    assert result.status == "succeeded"
    assert result.planned_updated_after == NOW - timedelta(days=30)
    assert sync_profile.last_successful_sync_at is not None
    assert sync_profile.last_attempted_sync_at is not None
    assert sync_profile.next_run_at is not None
    assert sync_profile.last_watermark_at is not None
    assert sync_profile.consecutive_failure_count == 0
    assert sync_profile.locked_at is None


def test_later_run_uses_existing_watermark(db_session, sync_profile):
    watermark = NOW - timedelta(hours=3)
    sync_profile.last_watermark_at = watermark
    db_session.commit()
    result = polling_worker.run_sync_profile_once(
        db_session,
        sync_profile.id,
        dry_run=True,
        now=NOW,
        settings=settings(),
    )
    assert result.planned_updated_after.replace(tzinfo=UTC) == watermark


def test_dry_run_does_not_advance_state(db_session, sync_profile):
    result = polling_worker.run_sync_profile_once(
        db_session,
        sync_profile.id,
        dry_run=True,
        now=NOW,
        settings=settings(),
    )
    db_session.refresh(sync_profile)
    assert result.status == "dry_run"
    assert sync_profile.last_watermark_at is None
    assert sync_profile.last_attempted_sync_at is None
    assert sync_profile.next_run_at is None


def test_failure_state_is_sanitized_and_watermark_unchanged(
    monkeypatch, db_session, sync_profile
):
    def fail(*_args, **_kwargs):
        raise RuntimeError("secret-value Authorization: Bearer token-value")

    monkeypatch.setattr(polling_worker, "sync_connection", fail)
    result = polling_worker.run_sync_profile_once(
        db_session,
        sync_profile.id,
        now=NOW,
        settings=settings(),
    )
    db_session.refresh(sync_profile)
    assert result.status == "failed"
    assert sync_profile.last_watermark_at is None
    assert sync_profile.last_attempted_sync_at is not None
    assert sync_profile.next_run_at is not None
    assert sync_profile.consecutive_failure_count == 1
    assert sync_profile.last_error_code == "RuntimeError"
    assert "secret-value" not in sync_profile.last_error_message
    assert "token-value" not in sync_profile.last_error_message


def test_due_worker_summary_defaults_to_dry_run(db_session, sync_profile):
    summary = polling_worker.run_due_profiles_once(
        db_session, now=NOW, settings=settings()
    )
    assert summary.dry_run is True
    assert summary.due_profiles_count == 1
    assert summary.attempted_count == 1
    assert summary.succeeded_count == 1
    assert summary.failed_count == 0
