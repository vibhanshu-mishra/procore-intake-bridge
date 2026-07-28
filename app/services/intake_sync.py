from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connections import DMSAConnection
from app.models.intake_records import IntakeAttachment, IntakeRecord
from app.models.sync_runs import SyncRun
from app.schemas.sync import NormalizedRecord, SyncSummary
from app.services.attachment_manifest import build_attachment_manifest
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
) -> tuple[list[tuple[dict, NormalizedRecord]], list]:
    collected = []
    manifest = []
    for project_id in connection.permitted_project_ids:
        sources = []
        if "rfis" in connection.enabled_tools:
            sources.append(("rfi", list_rfis_for_project(connection, project_id)))
        if "submittals" in connection.enabled_tools:
            sources.append(("submittal", list_submittals_for_project(connection, project_id)))
        for source_type, items in sources:
            for item in items:
                collected.append((item, _normalize(source_type, item)))
                manifest.extend(build_attachment_manifest(source_type, item))
    return collected, manifest


def sync_connection(session: Session, connection: DMSAConnection, dry_run: bool) -> SyncSummary:
    collected, manifest = collect_fixture_records(connection)
    if dry_run:
        return SyncSummary(
            dry_run=True,
            mode="fixture",
            sync_run_id=None,
            record_count=len(collected),
            attachment_count=len(manifest),
            records=[record for _, record in collected],
            attachment_manifest=manifest,
        )

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
        record.raw_payload_json = raw
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
    run.status = "completed"
    run.record_count = len(collected)
    run.attachment_count = len(manifest)
    run.completed_at = datetime.now(UTC)
    session.commit()
    return SyncSummary(
        dry_run=False,
        mode="fixture",
        sync_run_id=run.id,
        record_count=len(collected),
        attachment_count=len(manifest),
        records=[record for _, record in collected],
        attachment_manifest=manifest,
    )


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
