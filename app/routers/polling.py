from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.sync_profiles import PollingRunSummary
from app.services.polling_worker import run_due_profiles_once

router = APIRouter(prefix="/polling", tags=["polling"])


@router.post("/run-once", response_model=PollingRunSummary)
def polling_run_once(
    dry_run: bool = Query(default=True),
    session: Session = Depends(get_session),
) -> PollingRunSummary:
    return run_due_profiles_once(session, dry_run=dry_run)
