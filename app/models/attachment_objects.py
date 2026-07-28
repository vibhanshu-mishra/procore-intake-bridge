from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AttachmentObject(Base):
    __tablename__ = "attachment_objects"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "procore_project_id",
            "source_type",
            "procore_item_id",
            "procore_attachment_id",
            name="uq_attachment_source_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    intake_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("intake_records.id"), index=True
    )
    sync_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_runs.id"), index=True
    )
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("dmsa_connections.id"), index=True
    )
    sync_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_profiles.id"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(30), default="unknown")
    procore_project_id: Mapped[str | None] = mapped_column(String(100), index=True)
    procore_item_id: Mapped[str | None] = mapped_column(String(100))
    procore_attachment_id: Mapped[str | None] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(500))
    safe_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    source_url_present: Mapped[bool] = mapped_column(Boolean, default=False)
    source_url_hash: Mapped[str | None] = mapped_column(String(64))
    storage_backend: Mapped[str] = mapped_column(String(30), default="local")
    storage_key: Mapped[str] = mapped_column(String(1000))
    storage_path: Mapped[str] = mapped_column(String(1000))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    download_status: Mapped[str] = mapped_column(String(30), default="planned")
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    intake_record = relationship("IntakeRecord")
    sync_run = relationship("SyncRun")
    connection = relationship("DMSAConnection")
    sync_profile = relationship("SyncProfile")
