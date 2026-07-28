from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class OnboardingPacket(Base):
    __tablename__ = "onboarding_packets"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("dmsa_connections.id"), index=True
    )
    sync_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_profiles.id"), index=True
    )
    packet_name: Mapped[str] = mapped_column(String(200))
    packet_type: Mapped[str] = mapped_column(
        String(100), default="gc_owner_private_app_install"
    )
    recipient_company_name: Mapped[str] = mapped_column(String(200))
    recipient_contact_name: Mapped[str | None] = mapped_column(String(200))
    requester_company_name: Mapped[str] = mapped_column(String(200))
    requester_contact_name: Mapped[str | None] = mapped_column(String(200))
    app_name: Mapped[str] = mapped_column(String(200))
    app_version_key_ref: Mapped[str | None] = mapped_column(String(255))
    requested_project_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_tools_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_permissions_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    safety_summary_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    generated_markdown: Mapped[str] = mapped_column(Text)
    generated_json: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    connection = relationship("DMSAConnection")
    sync_profile = relationship("SyncProfile")
