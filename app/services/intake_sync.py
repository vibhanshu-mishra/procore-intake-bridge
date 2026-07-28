from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connections import DMSAConnection
from app.models.intake_records import IntakeAttachment, IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.attachments import AttachmentPlanRequest
from app.schemas.sync import NormalizedRecord, SyncSummary
from app.services.attachment_manifest import build_attachment_manifest
from app.services.attachment_storage import (
    attachment_plan_result,
    create_attachment_manifest_record,
)
from app.services.procore_client import list_rfis_for_project, list_submittals_for_project


def _normalize(source_type: str, item: dict) -> NormalizedRecord:
    return NormalizedRecord(
        source_type=source_type,
        procore_project_id=str(item["project_id"]),
        procore_item_id=str(item["id"]),
        number=str(item["number"]),
        title=item["title"],
        status=item["status"],
        due_date=item.get("due_date"),
        received_at=item.get("received_at"),
        updated_at=item.get("updated_at"),
        attachment_count=len(item.get("attachments", [])),
    )


def collect_fixture_records(
    connection: DMSAConnection,
    procore_project_id: str | None = None,
    sync_rfis: bool = True,
    sync_submittals: bool = True,
    updated_after: datetime | None = None,
) -> tuple[list[tuple[dict, NormalizedRecord]], list]:
    collected = []
    manifest = []
    project_ids = (
        [procore_project_id]
        if procore_project_id is not None
        else connection.permitted_project_ids
    )
    for project_id in project_ids:
        sources = []
        if sync_rfis and "rfis" in connection.enabled_tools:
            sources.append(
                (
                    "rfi",
                    list_rfis_for_project(
                        connection, project_id, updated_after=updated_after
                    ),
                )
            )
        if sync_submittals and "submittals" in connection.enabled_tools:
            sources.append(
                (
                    "submittal",
                    list_submittals_for_project(
                        connection, project_id, updated_after=updated_after
                    ),
                )
            )
        for source_type, items in sources:
            for item in items:
                collected.append((item, _normalize(source_type, item)))
                manifest.extend(build_attachment_manifest(source_type, item))
    return collected, manifest


def sync_connection(
    session: Session,
    connection: DMSAConnection,
    dry_run: bool,
    *,
    procore_project_id: str | None = None,
    sync_rfis: bool = True,
    sync_submittals: bool = True,
    updated_after: datetime | None = None,
    mode: str = "fixture",
    commit: bool = True,
    sync_profile_id: int | None = None,
) -> SyncSummary:
    if mode not in {"fixture", "mock"}:
        raise ValueError("Live intake sync is not implemented in Phase A3.")
    collected, manifest = collect_fixture_records(
        connection,
        procore_project_id=procore_project_id,
        sync_rfis=sync_rfis,
        sync_submittals=sync_submittals,
        updated_after=updated_after,
    )
    planned_requests = [
        _attachment_request(
            connection,
            normalized,
            attachment,
            sync_profile_id=sync_profile_id,
        )
        for raw, normalized in collected
        for attachment in raw.get("attachments", [])
    ]
    if dry_run:
        attachment_plans = [
            attachment_plan_result(None, request) for request in planned_requests
        ]
        return SyncSummary(
            dry_run=True,
            mode="fixture",
            sync_run_id=None,
            record_count=len(collected),
            attachment_count=len(manifest),
            records=[record for _, record in collected],
            attachment_manifest=manifest,
            attachment_plans=attachment_plans,
        )

    attachment_plans = []
    run = SyncRun(connection_id=connection.id, mode="fixture", status="running")
    session.add(run)
    session.flush()
    for raw, normalized in collected:
        existing = session.scalar(
            select(IntakeRecord).where(
                IntakeRecord.source_type == normalized.source_type,
                IntakeRecord.procore_project_id == normalized.procore_project_id,
                IntakeRecord.procore_item_id == normalized.procore_item_id,
            )
        )
        record = existing or IntakeRecord(
            source_type=normalized.source_type,
            procore_project_id=normalized.procore_project_id,
            procore_item_id=normalized.procore_item_id,
            sync_run_id=run.id,
        )
        record.number = normalized.number
        record.title = normalized.title
        record.status = normalized.status
        record.due_date = date.fromisoformat(normalized.due_date) if normalized.due_date else None
        record.received_at = _datetime(normalized.received_at)
        record.source_updated_at = _datetime(normalized.updated_at)
        record.raw_payload_json = _sanitize_source_payload(raw)
        record.attachment_count = normalized.attachment_count
        record.sync_run_id = run.id
        if existing:
            record.attachments.clear()
        else:
            session.add(record)
        session.flush()
        for attachment in raw.get("attachments", []):
            record.attachments.append(
                IntakeAttachment(
                    procore_attachment_id=str(attachment["id"]),
                    filename=attachment["filename"],
                    content_type=attachment.get("content_type"),
                    source_url_redacted=None,
                )
            )
            request = _attachment_request(
                connection,
                normalized,
                attachment,
                intake_record_id=record.id,
                sync_run_id=run.id,
                sync_profile_id=sync_profile_id,
            )
            attachment_object = create_attachment_manifest_record(
                session, request, commit=False
            )
            attachment_plans.append(
                attachment_plan_result(attachment_object, request)
            )
    run.status = "completed"
    run.record_count = len(collected)
    run.attachment_count = len(manifest)
    run.completed_at = datetime.now(UTC)
    if commit:
        session.commit()
    else:
        session.flush()
    return SyncSummary(
        dry_run=False,
        mode="fixture",
        sync_run_id=run.id,
        record_count=len(collected),
        attachment_count=len(manifest),
        records=[record for _, record in collected],
        attachment_manifest=manifest,
        attachment_plans=attachment_plans,
    )


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _attachment_request(
    connection: DMSAConnection,
    normalized: NormalizedRecord,
    attachment: dict,
    *,
    intake_record_id: int | None = None,
    sync_run_id: int | None = None,
    sync_profile_id: int | None = None,
) -> AttachmentPlanRequest:
    return AttachmentPlanRequest(
        intake_record_id=intake_record_id,
        sync_run_id=sync_run_id,
        connection_id=connection.id,
        sync_profile_id=sync_profile_id,
        source_type=normalized.source_type,
        procore_project_id=normalized.procore_project_id,
        procore_item_id=normalized.procore_item_id,
        procore_attachment_id=str(attachment.get("id"))
        if attachment.get("id") is not None
        else None,
        original_filename=attachment.get("filename") or "attachment.bin",
        content_type=attachment.get("content_type"),
        size_bytes=attachment.get("size_bytes"),
        source_url=attachment.get("source_url"),
    )


def _sanitize_source_payload(value):
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if "url" in str(key).casefold()
                else _sanitize_source_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_source_payload(item) for item in value]
    return value
