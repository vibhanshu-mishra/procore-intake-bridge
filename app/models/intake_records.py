from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IntakeRecord(Base):
    __tablename__ = "intake_records"
    __table_args__ = (
        UniqueConstraint(
            "source_type", "procore_project_id", "procore_item_id", name="uq_source_item"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), index=True)
    procore_project_id: Mapped[str] = mapped_column(String(100), index=True)
    procore_item_id: Mapped[str] = mapped_column(String(100))
    number: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(100))
    due_date: Mapped[date | None] = mapped_column(Date)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload_json: Mapped[dict] = mapped_column(JSON)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    sync_run = relationship("SyncRun", back_populates="records")
    attachments = relationship(
        "IntakeAttachment", back_populates="record", cascade="all, delete-orphan"
    )


class IntakeAttachment(Base):
    __tablename__ = "intake_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    intake_record_id: Mapped[int] = mapped_column(ForeignKey("intake_records.id"), index=True)
    procore_attachment_id: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(200))
    source_url_redacted: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    record = relationship("IntakeRecord", back_populates="attachments")
