from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.sync_profiles import SyncProfile
from app.schemas.sync_profiles import PollingRunSummary, SyncProfileRunResult
from app.services.intake_sync import sync_connection


class SyncProfileLockedError(RuntimeError):
    pass


class SyncProfileDisabledError(RuntimeError):
    pass


class LivePollingDisabledError(RuntimeError):
    pass


class LivePollingNotImplementedError(RuntimeError):
    pass


def calculate_next_run_at(now: datetime, polling_interval_minutes: int) -> datetime:
    return now + timedelta(minutes=polling_interval_minutes)


def find_due_sync_profiles(session: Session, now: datetime) -> list[SyncProfile]:
    return list(
        session.scalars(
            select(SyncProfile)
            .where(
                SyncProfile.enabled.is_(True),
                or_(
                    SyncProfile.next_run_at.is_(None),
                    SyncProfile.next_run_at <= now,
                ),
            )
            .order_by(SyncProfile.id)
        )
    )


def acquire_sync_lock(
    session: Session,
    sync_profile: SyncProfile,
    lock_owner: str,
    now: datetime,
    settings: Settings | None = None,
) -> bool:
    timeout = (settings or get_settings()).sync_lock_timeout_minutes
    stale_before = now - timedelta(minutes=timeout)
    result = session.execute(
        update(SyncProfile)
        .where(
            SyncProfile.id == sync_profile.id,
            or_(
                SyncProfile.locked_at.is_(None),
                SyncProfile.locked_at <= stale_before,
            ),
        )
        .values(locked_at=now, lock_owner=lock_owner)
        .execution_options(synchronize_session=False)
    )
    session.commit()
    session.refresh(sync_profile)
    return result.rowcount == 1


def release_sync_lock(session: Session, sync_profile: SyncProfile) -> None:
    sync_profile.locked_at = None
    sync_profile.lock_owner = None
    session.commit()


def record_sync_success(
    sync_profile: SyncProfile,
    attempted_at: datetime,
    watermark_at: datetime,
) -> None:
    sync_profile.last_attempted_sync_at = attempted_at
    sync_profile.last_successful_sync_at = attempted_at
    sync_profile.last_watermark_at = watermark_at
    sync_profile.next_run_at = calculate_next_run_at(
        attempted_at, sync_profile.polling_interval_minutes
    )
    sync_profile.consecutive_failure_count = 0
    sync_profile.last_error_code = None
    sync_profile.last_error_message = None


def record_sync_failure(
    sync_profile: SyncProfile,
    attempted_at: datetime,
    error_code: str,
) -> None:
    sync_profile.last_attempted_sync_at = attempted_at
    sync_profile.next_run_at = calculate_next_run_at(
        attempted_at, sync_profile.polling_interval_minutes
    )
    sync_profile.consecutive_failure_count += 1
    sync_profile.last_error_code = _sanitize_error_code(error_code)
    sync_profile.last_error_message = (
        "Sync attempt failed; sensitive error details were intentionally omitted."
    )


def run_sync_profile_once(
    session: Session,
    sync_profile_id: int,
    mode: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
    lock_owner: str | None = None,
) -> SyncProfileRunResult:
    resolved_settings = settings or get_settings()
    run_started_at = now or datetime.now(UTC)
    sync_profile = session.get(SyncProfile, sync_profile_id)
    if sync_profile is None:
        raise LookupError("Sync profile not found.")
    effective_mode = mode or sync_profile.mode
    planned_watermark = sync_profile.last_watermark_at or (
        run_started_at - timedelta(days=resolved_settings.max_sync_lookback_days)
    )

    if not sync_profile.enabled and not force:
        raise SyncProfileDisabledError("Disabled sync profiles require force=true.")
    if _has_active_lock(sync_profile, run_started_at, resolved_settings):
        raise SyncProfileLockedError("Sync profile already has an active lock.")
    if effective_mode == "live":
        if not resolved_settings.procore_live_mode_enabled:
            raise LivePollingDisabledError(
                "Live polling is disabled by configuration."
            )
        raise LivePollingNotImplementedError(
            "Live polling is not implemented in Phase A3."
        )

    if dry_run:
        summary = sync_connection(
            session,
            sync_profile.connection,
            dry_run=True,
            procore_project_id=sync_profile.procore_project_id,
            sync_rfis=sync_profile.sync_rfis,
            sync_submittals=sync_profile.sync_submittals,
            updated_after=planned_watermark,
            mode="mock",
            commit=False,
        )
        return SyncProfileRunResult(
            sync_profile_id=sync_profile.id,
            status="dry_run",
            mode="mock",
            dry_run=True,
            planned_updated_after=planned_watermark,
            record_count=summary.record_count,
            attachment_count=summary.attachment_count,
            message="Dry run completed without local writes or watermark changes.",
        )

    if not acquire_sync_lock(
        session,
        sync_profile,
        lock_owner or resolved_settings.worker_id,
        run_started_at,
        resolved_settings,
    ):
        raise SyncProfileLockedError("Sync profile lock could not be acquired.")

    try:
        summary = sync_connection(
            session,
            sync_profile.connection,
            dry_run=False,
            procore_project_id=sync_profile.procore_project_id,
            sync_rfis=sync_profile.sync_rfis,
            sync_submittals=sync_profile.sync_submittals,
            updated_after=planned_watermark,
            mode="mock",
            commit=False,
        )
        record_sync_success(sync_profile, run_started_at, run_started_at)
        session.commit()
        return SyncProfileRunResult(
            sync_profile_id=sync_profile.id,
            status="succeeded",
            mode="mock",
            dry_run=False,
            planned_updated_after=planned_watermark,
            watermark_advanced_to=run_started_at,
            record_count=summary.record_count,
            attachment_count=summary.attachment_count,
            sync_run_id=summary.sync_run_id,
            message="Fixture sync completed and local sync state advanced.",
        )
    except Exception as exc:
        session.rollback()
        sync_profile = session.get(SyncProfile, sync_profile_id)
        record_sync_failure(sync_profile, run_started_at, type(exc).__name__)
        session.commit()
        return SyncProfileRunResult(
            sync_profile_id=sync_profile.id,
            status="failed",
            mode="mock",
            dry_run=False,
            planned_updated_after=planned_watermark,
            error_code=sync_profile.last_error_code,
            message=sync_profile.last_error_message,
        )
    finally:
        sync_profile = session.get(SyncProfile, sync_profile_id)
        release_sync_lock(session, sync_profile)


def run_due_profiles_once(
    session: Session,
    *,
    dry_run: bool = True,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> PollingRunSummary:
    resolved_settings = settings or get_settings()
    run_at = now or datetime.now(UTC)
    due_profiles = find_due_sync_profiles(session, run_at)
    results = []
    for profile in due_profiles:
        try:
            result = run_sync_profile_once(
                session,
                profile.id,
                dry_run=dry_run,
                now=run_at,
                settings=resolved_settings,
            )
        except (
            LivePollingDisabledError,
            LivePollingNotImplementedError,
            SyncProfileDisabledError,
            SyncProfileLockedError,
        ) as exc:
            result = SyncProfileRunResult(
                sync_profile_id=profile.id,
                status="skipped",
                mode=profile.mode,
                dry_run=dry_run,
                planned_updated_after=profile.last_watermark_at
                or (
                    run_at
                    - timedelta(days=resolved_settings.max_sync_lookback_days)
                ),
                error_code=type(exc).__name__,
                message=str(exc),
            )
        results.append(result)

    return PollingRunSummary(
        due_profiles_count=len(due_profiles),
        attempted_count=len(results),
        succeeded_count=sum(
            result.status in {"succeeded", "dry_run"} for result in results
        ),
        failed_count=sum(result.status == "failed" for result in results),
        skipped_count=sum(result.status == "skipped" for result in results),
        dry_run=dry_run,
        results=results,
    )


def _has_active_lock(
    sync_profile: SyncProfile, now: datetime, settings: Settings
) -> bool:
    if sync_profile.locked_at is None:
        return False
    locked_at = sync_profile.locked_at
    if locked_at.tzinfo is None:
        locked_at = locked_at.replace(tzinfo=UTC)
    return locked_at > now - timedelta(minutes=settings.sync_lock_timeout_minutes)


def _sanitize_error_code(value: str) -> str:
    return "".join(character for character in value if character.isalnum() or character == "_")[
        :100
    ] or "SyncError"
