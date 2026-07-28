from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.models.connections import DMSAConnection
from app.models.sync_profiles import SyncProfile
from app.schemas.sync_profiles import (
    SyncProfileCreate,
    SyncProfileRead,
    SyncProfileRunResult,
    SyncProfileState,
    SyncProfileUpdate,
)
from app.services.polling_worker import (
    LivePollingDisabledError,
    LivePollingNotImplementedError,
    SyncProfileDisabledError,
    SyncProfileLockedError,
    run_sync_profile_once,
)

router = APIRouter(prefix="/sync-profiles", tags=["sync-profiles"])


def get_sync_profile_or_404(profile_id: int, session: Session) -> SyncProfile:
    profile = session.get(SyncProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Sync profile not found")
    return profile


@router.get("", response_model=list[SyncProfileRead])
def list_sync_profiles(session: Session = Depends(get_session)) -> list[SyncProfile]:
    return list(session.scalars(select(SyncProfile).order_by(SyncProfile.id)))


@router.post("", response_model=SyncProfileRead, status_code=status.HTTP_201_CREATED)
def create_sync_profile(
    payload: SyncProfileCreate, session: Session = Depends(get_session)
) -> SyncProfile:
    connection = session.get(DMSAConnection, payload.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    if payload.procore_project_id not in connection.permitted_project_ids:
        raise HTTPException(
            status_code=422,
            detail="Project must be in the connection's permitted project allowlist.",
        )
    values = payload.model_dump()
    values["polling_interval_minutes"] = (
        payload.polling_interval_minutes
        or get_settings().default_polling_interval_minutes
    )
    profile = SyncProfile(**values)
    session.add(profile)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A sync profile already exists for this connection and project.",
        ) from exc
    session.refresh(profile)
    return profile


@router.get("/{sync_profile_id}", response_model=SyncProfileRead)
def get_sync_profile(
    sync_profile_id: int, session: Session = Depends(get_session)
) -> SyncProfile:
    return get_sync_profile_or_404(sync_profile_id, session)


@router.patch("/{sync_profile_id}", response_model=SyncProfileRead)
def update_sync_profile(
    sync_profile_id: int,
    payload: SyncProfileUpdate,
    session: Session = Depends(get_session),
) -> SyncProfile:
    profile = get_sync_profile_or_404(sync_profile_id, session)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(profile, field, value)
    if not profile.sync_rfis and not profile.sync_submittals:
        raise HTTPException(status_code=422, detail="At least one source must be enabled.")
    session.commit()
    session.refresh(profile)
    return profile


@router.post("/{sync_profile_id}/run-once", response_model=SyncProfileRunResult)
def run_profile_once(
    sync_profile_id: int,
    mode: Literal["mock", "live"] | None = Query(default=None),
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> SyncProfileRunResult:
    return _run_profile(session, sync_profile_id, mode, dry_run=False, force=force)


@router.post("/{sync_profile_id}/dry-run", response_model=SyncProfileRunResult)
def dry_run_profile(
    sync_profile_id: int,
    mode: Literal["mock", "live"] | None = Query(default=None),
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> SyncProfileRunResult:
    return _run_profile(session, sync_profile_id, mode, dry_run=True, force=force)


@router.get("/{sync_profile_id}/state", response_model=SyncProfileState)
def get_sync_profile_state(
    sync_profile_id: int, session: Session = Depends(get_session)
) -> SyncProfileState:
    profile = get_sync_profile_or_404(sync_profile_id, session)
    now = datetime.now(UTC)
    next_run_at = profile.next_run_at
    if next_run_at is not None and next_run_at.tzinfo is None:
        next_run_at = next_run_at.replace(tzinfo=UTC)
    return SyncProfileState(
        id=profile.id,
        enabled=profile.enabled,
        mode=profile.mode,
        due=profile.enabled
        and (next_run_at is None or next_run_at <= now),
        locked=profile.locked_at is not None,
        last_successful_sync_at=profile.last_successful_sync_at,
        last_attempted_sync_at=profile.last_attempted_sync_at,
        next_run_at=profile.next_run_at,
        last_watermark_at=profile.last_watermark_at,
        consecutive_failure_count=profile.consecutive_failure_count,
        last_error_code=profile.last_error_code,
        last_error_message=profile.last_error_message,
    )


def _run_profile(
    session: Session,
    profile_id: int,
    mode: str | None,
    *,
    dry_run: bool,
    force: bool,
) -> SyncProfileRunResult:
    try:
        return run_sync_profile_once(
            session,
            profile_id,
            mode=mode,
            dry_run=dry_run,
            force=force,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Sync profile not found") from exc
    except (
        SyncProfileDisabledError,
        SyncProfileLockedError,
        LivePollingDisabledError,
        LivePollingNotImplementedError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
