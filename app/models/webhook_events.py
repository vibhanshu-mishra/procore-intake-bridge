from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_webhook_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("dmsa_connections.id"), index=True
    )
    sync_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_profiles.id"), index=True
    )
    source: Mapped[str] = mapped_column(String(30), default="procore")
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(200), default="unknown")
    resource_type: Mapped[str] = mapped_column(String(30), default="unknown")
    action: Mapped[str] = mapped_column(String(30), default="unknown")
    procore_company_id: Mapped[str | None] = mapped_column(String(100), index=True)
    procore_project_id: Mapped[str | None] = mapped_column(String(100), index=True)
    procore_item_id: Mapped[str | None] = mapped_column(String(100))
    payload_json: Mapped[dict] = mapped_column(JSON)
    normalized_json: Mapped[dict] = mapped_column(JSON)
    signature_status: Mapped[str] = mapped_column(
        String(30), default="not_configured"
    )
    processing_status: Mapped[str] = mapped_column(String(30), default="queued")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
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

    connection = relationship("DMSAConnection")
    sync_profile = relationship("SyncProfile")
