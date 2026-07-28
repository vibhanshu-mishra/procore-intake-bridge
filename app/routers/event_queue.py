from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.webhooks import EventQueueRunResult
from app.services.event_queue import run_event_queue_once

router = APIRouter(prefix="/event-queue", tags=["event-queue"])


@router.post("/run-once", response_model=EventQueueRunResult)
def event_queue_run_once(
    dry_run: bool = Query(default=True),
    limit: int = Query(default=25, ge=1, le=100),
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> EventQueueRunResult:
    return run_event_queue_once(
        session,
        limit=limit,
        dry_run=dry_run,
        force=force,
    )
