from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.routers.connections import get_connection_or_404
from app.schemas.sync import SyncSummary
from app.services.intake_sync import sync_connection

router = APIRouter(prefix="/connections", tags=["sync"])


@router.post("/{connection_id}/sync/dry-run", response_model=SyncSummary)
def dry_run(connection_id: int, session: Session = Depends(get_session)) -> SyncSummary:
    return sync_connection(session, get_connection_or_404(connection_id, session), dry_run=True)


@router.post("/{connection_id}/sync/run", response_model=SyncSummary)
def run(connection_id: int, session: Session = Depends(get_session)) -> SyncSummary:
    return sync_connection(session, get_connection_or_404(connection_id, session), dry_run=False)
