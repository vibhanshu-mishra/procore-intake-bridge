from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class IntakeReviewState(Base):
    __tablename__ = "intake_review_states"
    __table_args__ = (
        UniqueConstraint("intake_record_id", name="uq_intake_review_state_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    intake_record_id: Mapped[int] = mapped_column(
        ForeignKey("intake_records.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    current_reason_code: Mapped[str | None] = mapped_column(String(60))
    current_reason_summary_sanitized: Mapped[str | None] = mapped_column(String(500))
    actor_hash: Mapped[str | None] = mapped_column(String(64))
    actor_label_masked: Mapped[str | None] = mapped_column(String(140))
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    intake_record = relationship("IntakeRecord")


class IntakeReviewLifecycleEvent(Base):
    __tablename__ = "intake_review_lifecycle_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    intake_record_id: Mapped[int] = mapped_column(
        ForeignKey("intake_records.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), index=True)
    reason_code: Mapped[str] = mapped_column(String(60))
    reason_summary_sanitized: Mapped[str] = mapped_column(String(500))
    actor_hash: Mapped[str | None] = mapped_column(String(64))
    actor_label_masked: Mapped[str | None] = mapped_column(String(140))
    request_id_hash: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(
        String(60), default="local_review_workspace"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    intake_record = relationship("IntakeRecord")
