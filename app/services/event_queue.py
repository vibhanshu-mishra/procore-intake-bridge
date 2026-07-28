from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.connections import DMSAConnection
from app.models.intake_records import IntakeRecord
from app.models.sync_profiles import SyncProfile
from app.models.webhook_events import WebhookEvent
from app.schemas.webhooks import EventProcessingResult, EventQueueRunResult
from app.security.webhook_signature import WebhookSignatureResult
from app.services.polling_worker import run_sync_profile_once
from app.services.webhook_normalizer import (
    normalize_procore_webhook_event,
    sanitize_payload,
)


class EventLockedError(RuntimeError):
    pass


def enqueue_webhook_event(
    session: Session,
    payload: dict[str, Any],
    headers: dict[str, str],
    signature_result: WebhookSignatureResult,
    *,
    persist: bool = True,
    now: datetime | None = None,
) -> tuple[WebhookEvent, bool]:
    received_at = now or datetime.now(UTC)
    normalized = normalize_procore_webhook_event(payload, headers)
    existing = session.scalar(
        select(WebhookEvent).where(
            WebhookEvent.event_id == normalized["event_id"]
        )
    )
    if existing is not None:
        return existing, True

    connection, profile = _find_mapping(
        session,
        normalized["procore_company_id"],
        normalized["procore_project_id"],
        normalized["resource_type"],
    )
    relevant = normalized["resource_type"] in {"rfi", "submittal"}
    event = WebhookEvent(
        connection_id=connection.id if connection else None,
        sync_profile_id=profile.id if profile else None,
        source="procore",
        event_id=normalized["event_id"],
        event_type=normalized["event_type"],
        resource_type=normalized["resource_type"],
        action=normalized["action"],
        procore_company_id=normalized["procore_company_id"],
        procore_project_id=normalized["procore_project_id"],
        procore_item_id=normalized["procore_item_id"],
        payload_json=sanitize_payload(payload),
        normalized_json=normalized,
        signature_status=signature_result.status,
        processing_status="queued" if relevant else "skipped",
        received_at=received_at,
        available_at=received_at,
        last_error_code=None if relevant else "UnknownResourceType",
        last_error_message=(
            None
            if relevant
            else "Event resource type is unknown and was safely skipped."
        ),
    )
    if not persist:
        return event, False
    session.add(event)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_id == normalized["event_id"]
            )
        )
        if existing is None:
            raise
        return existing, True
    session.refresh(event)
    return event, False


def list_webhook_events(
    session: Session,
    *,
    processing_status: str | None = None,
    resource_type: str | None = None,
) -> list[WebhookEvent]:
    statement = select(WebhookEvent)
    if processing_status:
        statement = statement.where(
            WebhookEvent.processing_status == processing_status
        )
    if resource_type:
        statement = statement.where(WebhookEvent.resource_type == resource_type)
    return list(session.scalars(statement.order_by(WebhookEvent.id.desc())))


def get_webhook_event(session: Session, event_id: int) -> WebhookEvent | None:
    return session.get(WebhookEvent, event_id)


def find_queued_events(
    session: Session, limit: int, now: datetime
) -> list[WebhookEvent]:
    return list(
        session.scalars(
            select(WebhookEvent)
            .where(
                WebhookEvent.processing_status == "queued",
                WebhookEvent.available_at <= now,
            )
            .order_by(WebhookEvent.received_at, WebhookEvent.id)
            .limit(limit)
        )
    )


def acquire_event_lock(
    session: Session,
    event: WebhookEvent,
    lock_owner: str,
    now: datetime,
    settings: Settings | None = None,
) -> bool:
    timeout = (settings or get_settings()).event_lock_timeout_minutes
    stale_before = now - timedelta(minutes=timeout)
    result = session.execute(
        update(WebhookEvent)
        .where(
            WebhookEvent.id == event.id,
            or_(
                WebhookEvent.locked_at.is_(None),
                WebhookEvent.locked_at <= stale_before,
            ),
        )
        .values(locked_at=now, lock_owner=lock_owner)
        .execution_options(synchronize_session=False)
    )
    session.commit()
    session.refresh(event)
    return result.rowcount == 1


def release_event_lock(session: Session, event: WebhookEvent) -> None:
    event.locked_at = None
    event.lock_owner = None
    session.commit()


def process_webhook_event_once(
    session: Session,
    event_id: int,
    force: bool = False,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> EventProcessingResult:
    resolved_settings = settings or get_settings()
    attempted_at = now or datetime.now(UTC)
    event = get_webhook_event(session, event_id)
    if event is None:
        raise LookupError("Webhook event not found.")
    if event.processing_status != "queued" and not force:
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="skipped",
            sync_profile_id=event.sync_profile_id,
            error_code="EventNotQueued",
            message="Event is not queued; replay or force is required.",
        )
    if _has_active_lock(event, attempted_at, resolved_settings):
        raise EventLockedError("Webhook event already has an active lock.")
    if event.failure_count >= resolved_settings.event_max_attempts:
        if not dry_run:
            _mark_failed(event, "MaxAttemptsExceeded")
            session.commit()
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="failed",
            sync_profile_id=event.sync_profile_id,
            error_code="MaxAttemptsExceeded",
            message="Event reached the configured maximum processing attempts.",
        )
    if event.resource_type not in {"rfi", "submittal"}:
        if not dry_run:
            _mark_skipped(event, "UnknownResourceType")
            session.commit()
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="skipped",
            error_code="UnknownResourceType",
            message="Unknown resource type was safely skipped.",
        )

    connection, profile = _find_mapping(
        session,
        event.procore_company_id,
        event.procore_project_id,
        event.resource_type,
    )
    if profile is None:
        if not dry_run:
            _mark_skipped(event, "NoMatchingSyncProfile")
            session.commit()
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="skipped",
            error_code="NoMatchingSyncProfile",
            message="No enabled mock sync profile matches this event.",
        )
    event.connection_id = connection.id
    event.sync_profile_id = profile.id

    if dry_run:
        before_count = session.scalar(select(IntakeRecord.id).limit(1))
        sync_result = run_sync_profile_once(
            session,
            profile.id,
            mode="mock",
            dry_run=True,
            now=attempted_at,
            settings=resolved_settings,
        )
        assert session.scalar(select(IntakeRecord.id).limit(1)) == before_count
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="dry_run",
            sync_profile_id=profile.id,
            sync_status=sync_result.status,
            record_count=sync_result.record_count,
            message="Event processing dry run completed without state changes.",
        )

    if not acquire_event_lock(
        session,
        event,
        resolved_settings.event_worker_id,
        attempted_at,
        resolved_settings,
    ):
        raise EventLockedError("Webhook event lock could not be acquired.")
    event.processing_status = "processing"
    session.commit()
    try:
        sync_result = run_sync_profile_once(
            session,
            profile.id,
            mode="mock",
            dry_run=False,
            now=attempted_at,
            settings=resolved_settings,
        )
        if sync_result.status != "succeeded":
            raise RuntimeError("Fixture sync profile run failed.")
        event = get_webhook_event(session, event_id)
        event.processing_status = "processed"
        event.processed_at = attempted_at
        event.last_error_code = None
        event.last_error_message = None
        session.commit()
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="processed",
            sync_profile_id=profile.id,
            sync_status=sync_result.status,
            record_count=sync_result.record_count,
            message="Event processed through the fixture sync profile.",
        )
    except Exception as exc:
        session.rollback()
        event = get_webhook_event(session, event_id)
        event.failure_count += 1
        event.processing_status = (
            "failed"
            if event.failure_count >= resolved_settings.event_max_attempts
            else "queued"
        )
        event.last_error_code = _safe_code(type(exc).__name__)
        event.last_error_message = (
            "Event processing failed; sensitive details were intentionally omitted."
        )
        event.available_at = attempted_at
        session.commit()
        return EventProcessingResult(
            webhook_event_id=event.id,
            status="failed",
            sync_profile_id=profile.id,
            error_code=event.last_error_code,
            message=event.last_error_message,
        )
    finally:
        event = get_webhook_event(session, event_id)
        release_event_lock(session, event)


def run_event_queue_once(
    session: Session,
    limit: int = 25,
    dry_run: bool = True,
    force: bool = False,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> EventQueueRunResult:
    run_at = now or datetime.now(UTC)
    resolved_settings = settings or get_settings()
    events = (
        _find_force_processable_events(session, limit, run_at)
        if force
        else find_queued_events(session, limit, run_at)
    )
    results = []
    for event in events:
        try:
            result = process_webhook_event_once(
                session,
                event.id,
                force=force,
                dry_run=dry_run,
                now=run_at,
                settings=resolved_settings,
            )
        except EventLockedError:
            result = EventProcessingResult(
                webhook_event_id=event.id,
                status="skipped",
                sync_profile_id=event.sync_profile_id,
                error_code="EventLocked",
                message="Event has an active processing lock.",
            )
        results.append(result)
    return EventQueueRunResult(
        queued_count=len(events),
        attempted_count=len(results),
        processed_count=sum(result.status == "processed" for result in results),
        skipped_count=sum(result.status == "skipped" for result in results),
        failed_count=sum(result.status == "failed" for result in results),
        dry_run=dry_run,
        results=results,
    )


def replay_webhook_event(
    session: Session, event: WebhookEvent, now: datetime | None = None
) -> WebhookEvent:
    event.processing_status = "queued"
    event.available_at = now or datetime.now(UTC)
    event.processed_at = None
    event.failure_count = 0
    event.last_error_code = None
    event.last_error_message = None
    event.locked_at = None
    event.lock_owner = None
    session.commit()
    session.refresh(event)
    return event


def _find_force_processable_events(
    session: Session, limit: int, now: datetime
) -> list[WebhookEvent]:
    return list(
        session.scalars(
            select(WebhookEvent)
            .where(
                WebhookEvent.processing_status.in_(["queued", "skipped", "failed"]),
                WebhookEvent.available_at <= now,
            )
            .order_by(WebhookEvent.received_at, WebhookEvent.id)
            .limit(limit)
        )
    )


def _find_mapping(
    session: Session,
    company_id: str | None,
    project_id: str | None,
    resource_type: str,
) -> tuple[DMSAConnection | None, SyncProfile | None]:
    if project_id is None:
        return None, None
    statement = (
        select(SyncProfile)
        .join(DMSAConnection)
        .where(
            SyncProfile.procore_project_id == project_id,
            SyncProfile.enabled.is_(True),
            SyncProfile.mode == "mock",
        )
        .order_by(SyncProfile.id)
    )
    if company_id is not None:
        statement = statement.where(DMSAConnection.procore_company_id == company_id)
    profiles = list(session.scalars(statement))
    for profile in profiles:
        supported = (
            resource_type == "rfi" and profile.sync_rfis
        ) or (
            resource_type == "submittal" and profile.sync_submittals
        )
        if supported:
            return profile.connection, profile
    return None, None


def _mark_skipped(event: WebhookEvent, code: str) -> None:
    event.processing_status = "skipped"
    event.processed_at = datetime.now(UTC)
    event.last_error_code = code
    event.last_error_message = "Event was safely skipped."


def _mark_failed(event: WebhookEvent, code: str) -> None:
    event.processing_status = "failed"
    event.last_error_code = code
    event.last_error_message = (
        "Event processing stopped after the configured maximum attempts."
    )


def _has_active_lock(
    event: WebhookEvent, now: datetime, settings: Settings
) -> bool:
    if event.locked_at is None:
        return False
    locked_at = event.locked_at
    if locked_at.tzinfo is None:
        locked_at = locked_at.replace(tzinfo=UTC)
    return locked_at > now - timedelta(minutes=settings.event_lock_timeout_minutes)


def _safe_code(value: str) -> str:
    return "".join(character for character in value if character.isalnum() or character == "_")[
        :100
    ] or "EventProcessingError"
