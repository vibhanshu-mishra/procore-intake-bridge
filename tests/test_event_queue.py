import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.security.webhook_signature import WebhookSignatureResult
from app.services import event_queue

FIXTURES = Path("app/fixtures/webhooks")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
SIGNATURE = WebhookSignatureResult(
    status="not_configured", verified=False, message="test"
)


def load(name):
    return json.loads((FIXTURES / name).read_text())


def settings(**overrides):
    return Settings(_env_file=None, **overrides)


def enqueue(session, name):
    event, duplicate = event_queue.enqueue_webhook_event(
        session, load(name), {}, SIGNATURE, now=NOW
    )
    assert duplicate is False
    return event


def test_find_queued_events(db_session):
    queued = enqueue(db_session, "rfi_created.json")
    enqueue(db_session, "unknown_event.json")
    assert event_queue.find_queued_events(db_session, 25, NOW) == [queued]


def test_event_lock_overlap_stale_recovery_release(db_session):
    event = enqueue(db_session, "rfi_created.json")
    config = settings(event_lock_timeout_minutes=30)
    assert event_queue.acquire_event_lock(
        db_session, event, "worker-one", NOW, config
    )
    assert not event_queue.acquire_event_lock(
        db_session, event, "worker-two", NOW + timedelta(minutes=5), config
    )
    assert event_queue.acquire_event_lock(
        db_session, event, "worker-two", NOW + timedelta(minutes=31), config
    )
    event_queue.release_event_lock(db_session, event)
    assert event.locked_at is None


def test_matching_rfi_event_processes_fixture_sync(
    db_session, sync_profile
):
    event = enqueue(db_session, "rfi_created.json")
    result = event_queue.process_webhook_event_once(
        db_session, event.id, now=NOW, settings=settings()
    )
    db_session.refresh(event)
    assert result.status == "processed"
    assert result.sync_profile_id == sync_profile.id
    assert event.processing_status == "processed"
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 2
    assert (
        db_session.scalar(select(func.count()).select_from(AttachmentObject))
        == 3
    )


def test_matching_submittal_event_processes_fixture_sync(
    db_session, sync_profile
):
    event = enqueue(db_session, "submittal_created.json")
    result = event_queue.process_webhook_event_once(
        db_session, event.id, now=NOW, settings=settings()
    )
    assert result.status == "processed"
    assert result.sync_profile_id == sync_profile.id


def test_event_without_matching_profile_is_skipped(db_session):
    event = enqueue(db_session, "rfi_created.json")
    result = event_queue.process_webhook_event_once(
        db_session, event.id, now=NOW, settings=settings()
    )
    db_session.refresh(event)
    assert result.status == "skipped"
    assert result.error_code == "NoMatchingSyncProfile"
    assert event.processing_status == "skipped"


def test_unknown_event_is_safely_skipped(db_session):
    event = enqueue(db_session, "unknown_event.json")
    result = event_queue.process_webhook_event_once(
        db_session, event.id, force=True, now=NOW, settings=settings()
    )
    assert result.status == "skipped"
    assert result.error_code == "UnknownResourceType"


def test_event_queue_dry_run_does_not_mutate_or_write(
    db_session, sync_profile
):
    event = enqueue(db_session, "rfi_created.json")
    summary = event_queue.run_event_queue_once(
        db_session, now=NOW, settings=settings()
    )
    db_session.refresh(event)
    assert summary.dry_run is True
    assert summary.results[0].status == "dry_run"
    assert event.processing_status == "queued"
    assert event.processed_at is None
    assert db_session.scalar(select(func.count()).select_from(IntakeRecord)) == 0


def test_event_queue_run_marks_processed(db_session, sync_profile):
    event = enqueue(db_session, "rfi_created.json")
    summary = event_queue.run_event_queue_once(
        db_session, dry_run=False, now=NOW, settings=settings()
    )
    db_session.refresh(event)
    assert summary.processed_count == 1
    assert event.processing_status == "processed"


def test_max_attempts_marks_failed(db_session, sync_profile):
    event = enqueue(db_session, "rfi_created.json")
    event.failure_count = 5
    db_session.commit()
    result = event_queue.process_webhook_event_once(
        db_session,
        event.id,
        now=NOW,
        settings=settings(event_max_attempts=5),
    )
    db_session.refresh(event)
    assert result.status == "failed"
    assert event.processing_status == "failed"


def test_failure_message_is_sanitized(
    monkeypatch, db_session, sync_profile
):
    event = enqueue(db_session, "rfi_created.json")

    def fail(*_args, **_kwargs):
        raise RuntimeError("Bearer secret-value Authorization token-value")

    monkeypatch.setattr(event_queue, "run_sync_profile_once", fail)
    result = event_queue.process_webhook_event_once(
        db_session, event.id, now=NOW, settings=settings()
    )
    db_session.refresh(event)
    assert result.status == "failed"
    assert event.failure_count == 1
    assert event.processing_status == "queued"
    assert "secret-value" not in event.last_error_message
    assert "token-value" not in event.last_error_message


def test_event_queue_api_and_polling_fallback(client, sync_profile):
    client.post("/webhooks/procore", json=load("rfi_created.json"))
    queue = client.post("/event-queue/run-once?dry_run=true")
    polling = client.post("/polling/run-once")
    assert queue.status_code == 200
    assert queue.json()["dry_run"] is True
    assert polling.status_code == 200
