from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.connections import DMSAConnection
from app.schemas.connections import ConnectionCreate, ConnectionRead
from app.schemas.health import ConnectionHealthResult
from app.services.connection_health import check_connection_health

router = APIRouter(prefix="/connections", tags=["connections"])


def get_connection_or_404(connection_id: int, session: Session) -> DMSAConnection:
    connection = session.get(DMSAConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.get("", response_model=list[ConnectionRead])
def list_connections(session: Session = Depends(get_session)) -> list[DMSAConnection]:
    return list(session.scalars(select(DMSAConnection).order_by(DMSAConnection.id)))


@router.post("", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED)
def create_connection(
    payload: ConnectionCreate, session: Session = Depends(get_session)
) -> DMSAConnection:
    connection = DMSAConnection(**payload.model_dump())
    session.add(connection)
    session.commit()
    session.refresh(connection)
    return connection


@router.get("/{connection_id}", response_model=ConnectionRead)
def get_connection(connection_id: int, session: Session = Depends(get_session)) -> DMSAConnection:
    return get_connection_or_404(connection_id, session)


@router.post("/{connection_id}/health-check", response_model=ConnectionHealthResult)
def health_check(
    connection_id: int,
    mode: Literal["mock", "live"] = Query(default="mock"),
    session: Session = Depends(get_session),
) -> ConnectionHealthResult:
    return check_connection_health(get_connection_or_404(connection_id, session), mode=mode)
