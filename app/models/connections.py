from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class ProcoreEnvironment(StrEnum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    DMSA_CLIENT_CREDENTIALS = "dmsa_client_credentials"


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DEGRADED = "degraded"
    REVOKED = "revoked"


class DMSAConnection(Base):
    __tablename__ = "dmsa_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    procore_company_id: Mapped[str] = mapped_column(String(100), index=True)
    environment: Mapped[ProcoreEnvironment] = mapped_column(
        Enum(ProcoreEnvironment), default=ProcoreEnvironment.SANDBOX
    )
    auth_mode: Mapped[AuthMode] = mapped_column(
        Enum(AuthMode), default=AuthMode.DMSA_CLIENT_CREDENTIALS
    )
    permitted_project_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled_tools: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["rfis", "submittals"])
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus), default=ConnectionStatus.PENDING
    )
    client_id_ref: Mapped[str | None] = mapped_column(String(255))
    secret_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    sync_runs = relationship("SyncRun", back_populates="connection")
    sync_profiles = relationship(
        "SyncProfile", back_populates="connection", cascade="all, delete-orphan"
    )
