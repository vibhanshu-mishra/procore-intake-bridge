import csv
import json
import re
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.intake_lifecycle import IntakeReviewLifecycleEvent
from app.schemas.operator_export_pack import (
    OperatorExportArtifactResult,
    OperatorExportAttachmentSummary,
    OperatorExportCombinedPacket,
    OperatorExportEventSummary,
    OperatorExportFilter,
    OperatorExportFormat,
    OperatorExportIntakeSummary,
    OperatorExportLifecycleSummary,
    OperatorExportMetadata,
    OperatorExportSection,
    OperatorExportStatus,
    OperatorExportTriageSummary,
)
from app.services.attachment_review import build_attachment_review_workspace_summary
from app.services.intake_lifecycle import build_lifecycle_summary
from app.services.intake_review_workspace import (
    build_intake_review_filter,
    build_intake_review_workspace_summary,
    hash_intake_review_identifier,
    list_intake_review_records,
    mask_intake_review_identifier,
    sanitize_intake_review_value,
)
from app.services.operator_triage_queue import build_operator_triage_summary


class OperatorExportPackError(ValueError):
    pass


class OperatorExportPackBlockedError(OperatorExportPackError):
    pass


URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(r"(?i)(?:bearer\s+\S+|(?:token|password|secret|client_secret)\s*[:=]\s*\S+)")
FILENAME = re.compile(r"(?i)\b[^\s/\\]+\.(?:pdf|png|jpe?g|gif|dwg|dxf|xlsx?|docx?|zip)\b")
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:official customer report|compliance (?:report|certificate|certification)|"
    r"(?:approved|approval granted)|procore status)\b"
)
SAFE_OUTPUT_ROOTS = {
    "operator-export-output",
    "review-export-output",
    "intake-export-output",
    "lifecycle-export-output",
    "triage-export-output",
    "attachment-export-output",
}


def sanitize_operator_export_value(value: Any) -> Any:
    return sanitize_intake_review_value(value)


def mask_operator_export_identifier(value: Any) -> str | None:
    return mask_intake_review_identifier(value)


def hash_operator_export_identifier(value: Any) -> str | None:
    return hash_intake_review_identifier(value)


def _configured_sections(settings: Settings) -> list[OperatorExportSection]:
    sections = [OperatorExportSection.COMBINED_PACKET]
    if settings.export_pack_include_intake_summary:
        sections.extend(
            [OperatorExportSection.INTAKE_SUMMARY, OperatorExportSection.INTAKE_RECORDS]
        )
    if settings.export_pack_include_lifecycle_summary:
        sections.append(OperatorExportSection.LIFECYCLE_SUMMARY)
    if settings.export_pack_include_event_summary:
        sections.append(OperatorExportSection.LIFECYCLE_EVENTS)
    if settings.export_pack_include_triage_summary:
        sections.append(OperatorExportSection.TRIAGE_SUMMARY)
    if settings.export_pack_include_attachment_summary:
        sections.append(OperatorExportSection.ATTACHMENT_SUMMARY)
    return sections


def build_operator_export_filter(
    settings: Settings,
    *,
    sections: list[str | OperatorExportSection] | None = None,
    formats: list[str | OperatorExportFormat] | None = None,
    max_records: int | None = None,
) -> OperatorExportFilter:
    try:
        selected_sections = (
            [OperatorExportSection(value) for value in sections]
            if sections is not None
            else _configured_sections(settings)
        )
        configured_formats = [
            value.strip()
            for value in settings.export_pack_default_formats.split(",")
            if value.strip()
        ]
        selected_formats = [
            OperatorExportFormat(value)
            for value in (formats if formats is not None else configured_formats)
        ]
    except ValueError as exc:
        raise OperatorExportPackError("Unsupported operator export selection.") from exc
    return OperatorExportFilter(
        sections=list(dict.fromkeys(selected_sections)),
        formats=list(dict.fromkeys(selected_formats)),
        max_records=min(
            max(max_records or settings.export_pack_max_records, 1),
            settings.export_pack_max_records,
        ),
    )


def _safe_configuration(settings: Settings) -> bool:
    return not any(
        (
            settings.export_pack_expose_raw_payloads,
            settings.export_pack_expose_source_urls,
            settings.export_pack_expose_signed_urls,
            settings.export_pack_expose_storage_keys,
            settings.export_pack_expose_private_paths,
            settings.export_pack_expose_original_filenames,
            settings.export_pack_expose_contents,
        )
    )


def _export_status(settings: Settings) -> OperatorExportStatus:
    if not settings.export_pack_enabled:
        return OperatorExportStatus.DISABLED
    if settings.export_pack_fail_closed and not _safe_configuration(settings):
        return OperatorExportStatus.NEEDS_CONFIGURATION
    return OperatorExportStatus.AVAILABLE


def build_operator_export_metadata(session: Session, settings: Settings) -> OperatorExportMetadata:
    return OperatorExportMetadata(
        status=_export_status(settings),
        generated_at=datetime.now(UTC),
        local_record_limit=settings.export_pack_max_records,
    )


def _intake_records(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    page_number = 1
    page_size = min(filters.max_records, settings.intake_review_workspace_max_page_size)
    while len(records) < filters.max_records:
        page = list_intake_review_records(
            session,
            build_intake_review_filter(
                settings,
                page=page_number,
                page_size=page_size,
                sort="received_at_desc",
            ),
            settings,
        )
        for item in page.items:
            records.append(
                {
                    "local_record_reference": f"local-record-{item.record_id}",
                    "tool": item.tool.value,
                    "display_number": item.display_number,
                    "title": sanitize_operator_export_value(item.title),
                    "source_status": sanitize_operator_export_value(item.source_status),
                    "lifecycle_status": item.lifecycle_status.value,
                    "received_at": (item.received_at.isoformat() if item.received_at else None),
                    "manifest_count": (
                        item.attachment_summary.manifest_count if item.attachment_summary else 0
                    ),
                }
            )
            if len(records) >= filters.max_records:
                break
        if not page.items or page_number >= page.total_pages:
            break
        page_number += 1
    return records


def build_operator_export_intake_summary(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportIntakeSummary:
    status = _export_status(settings)
    if status is not OperatorExportStatus.AVAILABLE:
        return OperatorExportIntakeSummary(status=status)
    summary = build_intake_review_workspace_summary(session, settings)
    records = (
        _intake_records(session, filters, settings)
        if OperatorExportSection.INTAKE_RECORDS in filters.sections
        else []
    )
    result = OperatorExportIntakeSummary(
        status=(
            OperatorExportStatus.AVAILABLE if summary.total_records else OperatorExportStatus.EMPTY
        ),
        total_records=summary.total_records,
        exported_records=len(records),
        rfi_records=summary.rfi_records,
        submittal_records=summary.submittal_records,
        unknown_records=summary.unknown_records,
        records_with_manifests=summary.records_with_manifests,
        records=records,
    )
    validate_operator_export_safe(result)
    return result


def build_operator_export_lifecycle_summary(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportLifecycleSummary:
    status = _export_status(settings)
    if status is not OperatorExportStatus.AVAILABLE:
        return OperatorExportLifecycleSummary(status=status)
    summary = build_lifecycle_summary(session, settings)
    result = OperatorExportLifecycleSummary(
        status=(
            OperatorExportStatus.AVAILABLE
            if summary.total_states or summary.total_events
            else OperatorExportStatus.EMPTY
        ),
        total_states=summary.total_states,
        total_events=summary.total_events,
        counts_by_status={key.value: value for key, value in summary.counts_by_status.items()},
    )
    validate_operator_export_safe(result)
    return result


def build_operator_export_triage_summary(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportTriageSummary:
    status = _export_status(settings)
    if status is not OperatorExportStatus.AVAILABLE:
        return OperatorExportTriageSummary(status=status)
    summary = build_operator_triage_summary(session, settings)
    result = OperatorExportTriageSummary(
        status=(
            OperatorExportStatus.AVAILABLE if summary.total_records else OperatorExportStatus.EMPTY
        ),
        total_records=summary.total_records,
        bucket_counts={item.bucket.value: item.count for item in summary.buckets},
        lifecycle_distribution={
            key.value: value for key, value in summary.lifecycle_distribution.items()
        },
    )
    validate_operator_export_safe(result)
    return result


def build_operator_export_attachment_summary(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportAttachmentSummary:
    status = _export_status(settings)
    if status is not OperatorExportStatus.AVAILABLE:
        return OperatorExportAttachmentSummary(status=status)
    summary = build_attachment_review_workspace_summary(session, settings)
    result = OperatorExportAttachmentSummary(
        status=(
            OperatorExportStatus.AVAILABLE if summary.total_records else OperatorExportStatus.EMPTY
        ),
        total_records=summary.total_records,
        records_with_manifests=summary.records_with_manifests,
        records_without_manifests=summary.records_without_manifests,
        planned_attachments=summary.planned_attachments,
        stored_metadata_attachments=summary.stored_metadata_attachments,
        skipped_attachments=summary.skipped_attachments,
        blocked_attachments=summary.blocked_attachments,
    )
    validate_operator_export_safe(result)
    return result


def build_operator_export_event_summary(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportEventSummary:
    status = _export_status(settings)
    table_available = inspect(session.get_bind()).has_table(
        IntakeReviewLifecycleEvent.__tablename__
    )
    if status is not OperatorExportStatus.AVAILABLE:
        return OperatorExportEventSummary(status=status)
    if not table_available:
        return OperatorExportEventSummary(status=OperatorExportStatus.EMPTY)
    total = session.scalar(select(func.count()).select_from(IntakeReviewLifecycleEvent)) or 0
    rows = list(
        session.scalars(
            select(IntakeReviewLifecycleEvent)
            .order_by(
                IntakeReviewLifecycleEvent.created_at.desc(),
                IntakeReviewLifecycleEvent.id.desc(),
            )
            .limit(filters.max_records)
        )
    )
    transitions: dict[str, int] = {}
    reasons: dict[str, int] = {}
    events = []
    for row in rows:
        transition = f"{row.from_status}->{row.to_status}"
        transitions[transition] = transitions.get(transition, 0) + 1
        reasons[row.reason_code] = reasons.get(row.reason_code, 0) + 1
        events.append(
            {
                "local_event_reference": f"local-event-{row.id}",
                "transition": transition,
                "reason_code": sanitize_operator_export_value(row.reason_code),
                "created_at": row.created_at.isoformat(),
            }
        )
    result = OperatorExportEventSummary(
        status=OperatorExportStatus.AVAILABLE if total else OperatorExportStatus.EMPTY,
        total_events=total,
        exported_events=len(events),
        counts_by_transition=transitions,
        counts_by_reason=reasons,
        events=events,
    )
    validate_operator_export_safe(result)
    return result


def build_operator_export_combined_packet(
    session: Session, filters: OperatorExportFilter, settings: Settings
) -> OperatorExportCombinedPacket:
    packet = OperatorExportCombinedPacket(
        metadata=build_operator_export_metadata(session, settings),
        intake=(
            build_operator_export_intake_summary(session, filters, settings)
            if OperatorExportSection.INTAKE_SUMMARY in filters.sections
            else None
        ),
        lifecycle=(
            build_operator_export_lifecycle_summary(session, filters, settings)
            if OperatorExportSection.LIFECYCLE_SUMMARY in filters.sections
            else None
        ),
        triage=(
            build_operator_export_triage_summary(session, filters, settings)
            if OperatorExportSection.TRIAGE_SUMMARY in filters.sections
            else None
        ),
        attachments=(
            build_operator_export_attachment_summary(session, filters, settings)
            if OperatorExportSection.ATTACHMENT_SUMMARY in filters.sections
            else None
        ),
        events=(
            build_operator_export_event_summary(session, filters, settings)
            if OperatorExportSection.LIFECYCLE_EVENTS in filters.sections
            else None
        ),
    )
    validate_operator_export_safe(packet)
    return packet


def render_operator_export_json(packet: OperatorExportCombinedPacket) -> str:
    validate_operator_export_safe(packet)
    rendered = json.dumps(packet.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    validate_operator_export_safe(rendered)
    return rendered


def render_operator_export_markdown(packet: OperatorExportCombinedPacket) -> str:
    lines = [
        "# Local Operator Export Summary",
        "",
        "Sanitized local metadata summary only. This is not an official external report.",
        "",
        f"- Status: `{packet.metadata.status.value}`",
        f"- Local record cap: `{packet.metadata.local_record_limit}`",
        "- Raw payloads exposed: `false`",
        "- Attachment contents exposed: `false`",
        "- External calls made: `false`",
    ]
    if packet.intake:
        lines.extend(
            [
                "",
                "## Intake",
                "",
                f"- Total local records: `{packet.intake.total_records}`",
                f"- Exported record summaries: `{packet.intake.exported_records}`",
            ]
        )
    if packet.lifecycle:
        lines.extend(
            [
                "",
                "## Local lifecycle",
                "",
                f"- Local states: `{packet.lifecycle.total_states}`",
                f"- Local events: `{packet.lifecycle.total_events}`",
            ]
        )
    if packet.triage:
        lines.extend(
            [
                "",
                "## Triage",
                "",
                f"- Local records: `{packet.triage.total_records}`",
                f"- Description: {packet.triage.description}",
            ]
        )
    if packet.attachments:
        lines.extend(
            [
                "",
                "## Attachment metadata",
                "",
                f"- Records with manifests: `{packet.attachments.records_with_manifests}`",
                f"- Planned attachments: `{packet.attachments.planned_attachments}`",
                "- Metadata only: `true`",
            ]
        )
    if packet.events:
        lines.extend(
            [
                "",
                "## Lifecycle event metadata",
                "",
                f"- Total events: `{packet.events.total_events}`",
                f"- Exported event summaries: `{packet.events.exported_events}`",
            ]
        )
    rendered = "\n".join(lines) + "\n"
    validate_operator_export_safe(rendered)
    return rendered


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, default=str)
    else:
        text = str(value)
    text = sanitize_operator_export_value(text)
    if text.startswith(("=", "+", "-", "@")):
        text = f"'{text}"
    return text


def render_operator_export_csv_sections(
    packet: OperatorExportCombinedPacket,
) -> dict[str, str]:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["section", "record_type", "key", "value"])

    def add(section: str, record_type: str, key: str, value: Any) -> None:
        writer.writerow([_csv_cell(item) for item in (section, record_type, key, value)])

    add("metadata", "summary", "status", packet.metadata.status.value)
    add("metadata", "summary", "local_record_limit", packet.metadata.local_record_limit)
    for section_name in ("intake", "lifecycle", "triage", "attachments", "events"):
        section = getattr(packet, section_name)
        if section is None:
            continue
        data = section.model_dump(mode="json")
        nested = data.pop("records", data.pop("events", []))
        for key, value in data.items():
            add(section_name, "summary", key, value)
        for index, item in enumerate(nested, start=1):
            for key, value in item.items():
                add(section_name, f"item-{index}", key, value)
    rendered = output.getvalue()
    validate_operator_export_safe(rendered)
    return {"combined.operator-export.csv": rendered}


def validate_operator_export_safe(
    packet_or_text: BaseModel | dict[str, Any] | str,
) -> None:
    if isinstance(packet_or_text, BaseModel):
        payload: Any = packet_or_text.model_dump(mode="json")
    else:
        payload = packet_or_text
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    keys = (
        {str(key).casefold() for key in _walk_keys(payload)}
        if not isinstance(payload, str)
        else set()
    )
    forbidden_keys = {
        "raw_payload",
        "raw_payload_json",
        "source_url",
        "signed_url",
        "storage_key",
        "storage_path",
        "original_filename",
        "safe_filename",
        "file_contents",
        "content_bytes",
        "procore_project_id",
        "procore_item_id",
        "procore_attachment_id",
        "actor_label",
        "actor_hash",
    }
    unsafe_claim = any(
        UNSAFE_CLAIM.search(line)
        and not re.search(r"(?i)\b(?:not|no|never|does not|isn't|is not)\b", line)
        for line in text.splitlines()
    )
    if (
        keys & forbidden_keys
        or URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
        or FILENAME.search(text)
        or unsafe_claim
    ):
        raise OperatorExportPackBlockedError("Unsafe operator export content was blocked.")


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    if root in {Path("."), Path(".."), Path("/")} or ".." in root.parts:
        raise OperatorExportPackBlockedError("Operator export path was blocked.")
    temporary_absolute = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-operator-export-")
        and root.parent == Path("/tmp")
    )
    if root.is_absolute() and not temporary_absolute:
        raise OperatorExportPackBlockedError("Operator export path was blocked.")
    if not root.is_absolute() and root.parts[:1] not in {(name,) for name in SAFE_OUTPUT_ROOTS}:
        raise OperatorExportPackBlockedError("Operator export path was blocked.")
    return root


def write_operator_export_artifacts(
    packet: OperatorExportCombinedPacket,
    output_root: Path,
    formats: list[OperatorExportFormat],
) -> OperatorExportArtifactResult:
    validate_operator_export_safe(packet)
    root = _safe_output_root(Path(output_root))
    root.mkdir(parents=True, exist_ok=True)
    contents: dict[str, str] = {}
    if OperatorExportFormat.JSON in formats:
        contents["combined.operator-export.json"] = render_operator_export_json(packet)
    if OperatorExportFormat.MARKDOWN in formats:
        contents["combined.operator-export.md"] = render_operator_export_markdown(packet)
    if OperatorExportFormat.CSV in formats:
        contents.update(render_operator_export_csv_sections(packet))
    for name, content in contents.items():
        target = root / name
        if target.parent != root:
            raise OperatorExportPackBlockedError("Operator export path was blocked.")
        target.write_text(content, encoding="utf-8")
    return OperatorExportArtifactResult(
        status=OperatorExportStatus.WRITTEN,
        output_directory=root.name,
        files=sorted(contents),
        formats=formats,
    )
