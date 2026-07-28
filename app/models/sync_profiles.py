from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class SyncProfile(Base):
    __tablename__ = "sync_profiles"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "procore_project_id",
            name="uq_sync_profile_connection_project",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("dmsa_connections.id"), index=True
    )
    procore_project_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_rfis: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_submittals: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mode: Mapped[str] = mapped_column(String(20), default="mock")
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_attempted_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_watermark_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lock_owner: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    connection = relationship("DMSAConnection", back_populates="sync_profiles")
