from pathlib import PurePath

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.attachment_objects import AttachmentObject
from app.models.connections import DMSAConnection
from app.models.intake_records import IntakeRecord
from app.models.onboarding_packets import OnboardingPacket
from app.models.sync_profiles import SyncProfile
from app.models.sync_runs import SyncRun
from app.models.webhook_events import WebhookEvent
from app.schemas.admin import (
    AdminCountCard,
    AdminOverview,
    AdminRecentAttachment,
    AdminRecentConnection,
    AdminRecentIntakeRecord,
    AdminRecentOnboardingPacket,
    AdminRecentSyncProfile,
    AdminRecentSyncRun,
    AdminRecentWebhookEvent,
    AdminSafetyStatus,
)
from app.security.admin_access import (
    get_admin_auth_config_summary,
    mask_identifier,
    redact_admin_value,
)


def build_connection_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentConnection]:
    rows = session.scalars(
        select(DMSAConnection)
        .order_by(DMSAConnection.id.desc())
        .limit(limit)
    )
    return [
        AdminRecentConnection(
            id=row.id,
            display_name=f"Connection #{row.id}",
            company_id_masked=mask_identifier(row.procore_company_id) or "",
            environment=row.environment.value,
            status=row.status.value,
            project_count=len(row.permitted_project_ids),
            created_at=row.created_at,
        )
        for row in rows
    ]


def build_sync_profile_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentSyncProfile]:
    rows = session.scalars(
        select(SyncProfile).order_by(SyncProfile.id.desc()).limit(limit)
    )
    return [
        AdminRecentSyncProfile(
            id=row.id,
            connection_id=row.connection_id,
            display_name=f"Sync profile #{row.id}",
            project_id_masked=mask_identifier(row.procore_project_id) or "",
            enabled=row.enabled,
            mode=row.mode,
            next_run_at=row.next_run_at,
            consecutive_failure_count=row.consecutive_failure_count,
        )
        for row in rows
    ]


def build_sync_run_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentSyncRun]:
    rows = session.scalars(
        select(SyncRun).order_by(SyncRun.id.desc()).limit(limit)
    )
    return [
        AdminRecentSyncRun(
            id=row.id,
            connection_id=row.connection_id,
            mode=row.mode,
            status=row.status,
            record_count=row.record_count,
            attachment_count=row.attachment_count,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
        for row in rows
    ]


def build_intake_record_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentIntakeRecord]:
    rows = session.scalars(
        select(IntakeRecord).order_by(IntakeRecord.id.desc()).limit(limit)
    )
    return [
        AdminRecentIntakeRecord(
            id=row.id,
            source_type=row.source_type,
            project_id_masked=mask_identifier(row.procore_project_id) or "",
            item_id_masked=mask_identifier(row.procore_item_id) or "",
            number_masked=mask_identifier(row.number) or "",
            status=str(redact_admin_value(row.status))[:100],
            attachment_count=row.attachment_count,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def build_attachment_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentAttachment]:
    rows = session.scalars(
        select(AttachmentObject)
        .order_by(AttachmentObject.id.desc())
        .limit(limit)
    )
    return [
        AdminRecentAttachment(
            id=row.id,
            intake_record_id=row.intake_record_id,
            source_type=row.source_type,
            project_id_masked=mask_identifier(row.procore_project_id),
            filename_display=_safe_filename_display(row),
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            download_status=row.download_status,
            checksum_present=bool(row.checksum_sha256),
        )
        for row in rows
    ]


def build_webhook_event_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentWebhookEvent]:
    rows = session.scalars(
        select(WebhookEvent).order_by(WebhookEvent.id.desc()).limit(limit)
    )
    return [
        AdminRecentWebhookEvent(
            id=row.id,
            event_id_masked=mask_identifier(row.event_id) or "",
            event_type=str(redact_admin_value(row.event_type))[:200],
            resource_type=row.resource_type,
            action=row.action,
            processing_status=row.processing_status,
            failure_count=row.failure_count,
            received_at=row.received_at,
        )
        for row in rows
    ]


def build_onboarding_packet_summary(
    session: Session, limit: int = 25
) -> list[AdminRecentOnboardingPacket]:
    rows = session.scalars(
        select(OnboardingPacket)
        .order_by(OnboardingPacket.id.desc())
        .limit(limit)
    )
    return [
        AdminRecentOnboardingPacket(
            id=row.id,
            display_name=f"Onboarding packet #{row.id}",
            connection_id=row.connection_id,
            status=row.status,
            project_count=len(row.requested_project_ids_json),
            created_at=row.created_at,
        )
        for row in rows
    ]


def build_safety_status(settings: Settings | None = None) -> AdminSafetyStatus:
    resolved = settings or get_settings()
    auth = get_admin_auth_config_summary(resolved)
    return AdminSafetyStatus(
        live_mode_enabled=resolved.procore_live_mode_enabled,
        webhook_signature_required=resolved.require_webhook_signature,
        fixture_only_downloads=resolved.attachment_fixture_downloads_only,
        admin_dashboard_enabled=resolved.admin_dashboard_enabled,
        admin_token_required=auth.token_required,
        admin_auth_mode=auth.mode,
        admin_token_header_name=auth.token_header_name,
        admin_primary_ref_configured=auth.primary_token_ref_configured,
        admin_rotation_ref_configured=auth.rotation_token_ref_configured,
        admin_provider_health_status=auth.provider_health_status,
        deployment_routes_protected=auth.deployment_routes_protected,
        production_auth_warning=(
            "Local dashboard only. Add real application/platform authentication "
            "and network restrictions before any production exposure."
        ),
    )


def build_admin_overview(
    session: Session,
    settings: Settings | None = None,
    recent_limit: int = 5,
) -> AdminOverview:
    cards = [
        _card(
            "Connections",
            _count(session, DMSAConnection),
            _breakdown(session, DMSAConnection.status),
            "No connections yet",
        ),
        _card(
            "Sync profiles",
            _count(session, SyncProfile),
            {
                "enabled": _count_where(
                    session, SyncProfile, SyncProfile.enabled.is_(True)
                ),
                "disabled": _count_where(
                    session, SyncProfile, SyncProfile.enabled.is_(False)
                ),
            },
            "No sync profiles yet",
        ),
        _card(
            "Sync runs",
            _count(session, SyncRun),
            _breakdown(session, SyncRun.status),
            "No sync runs yet",
        ),
        _card(
            "Intake records",
            _count(session, IntakeRecord),
            _breakdown(session, IntakeRecord.source_type),
            "No intake records yet",
        ),
        _card(
            "Attachments",
            _count(session, AttachmentObject),
            _breakdown(session, AttachmentObject.download_status),
            "No attachment manifests yet",
        ),
        _card(
            "Webhook events",
            _count(session, WebhookEvent),
            _breakdown(session, WebhookEvent.processing_status),
            "No webhook events yet",
        ),
        _card(
            "Onboarding packets",
            _count(session, OnboardingPacket),
            _breakdown(session, OnboardingPacket.status),
            "No onboarding packets yet",
        ),
    ]
    return AdminOverview(
        system_readiness="ready",
        count_cards=cards,
        safety=build_safety_status(settings),
        recent_connections=build_connection_summary(session, recent_limit),
        recent_sync_profiles=build_sync_profile_summary(session, recent_limit),
        recent_sync_runs=build_sync_run_summary(session, recent_limit),
        recent_intake_records=build_intake_record_summary(
            session, recent_limit
        ),
        recent_attachments=build_attachment_summary(session, recent_limit),
        recent_webhook_events=build_webhook_event_summary(
            session, recent_limit
        ),
        recent_onboarding_packets=build_onboarding_packet_summary(
            session, recent_limit
        ),
    )


def _count(session: Session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _count_where(session: Session, model, criterion) -> int:
    return (
        session.scalar(select(func.count()).select_from(model).where(criterion))
        or 0
    )


def _breakdown(session: Session, column) -> dict[str, int]:
    rows = session.execute(select(column, func.count()).group_by(column))
    return {
        getattr(value, "value", str(value)): count for value, count in rows
    }


def _card(
    label: str,
    count: int,
    breakdown: dict[str, int],
    empty_message: str,
) -> AdminCountCard:
    return AdminCountCard(
        label=label,
        count=count,
        breakdown=breakdown,
        empty_message=empty_message if count == 0 else None,
    )


def _safe_filename_display(row: AttachmentObject) -> str:
    suffix = PurePath(row.safe_filename).suffix[:20]
    return f"attachment-{row.id}{suffix}"
