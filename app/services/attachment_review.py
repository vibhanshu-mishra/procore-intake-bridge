import json
import math
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_records import IntakeRecord
from app.schemas.attachment_review import (
    AttachmentReviewAvailability,
    AttachmentReviewChecksumStatus,
    AttachmentReviewFileCategory,
    AttachmentReviewFilter,
    AttachmentReviewItem,
    AttachmentReviewManifestSummary,
    AttachmentReviewPage,
    AttachmentReviewRecordDetail,
    AttachmentReviewRecordSummary,
    AttachmentReviewSort,
    AttachmentReviewStatus,
    AttachmentReviewStorageStatus,
    AttachmentReviewWorkspaceSummary,
)
from app.schemas.intake_review_workspace import IntakeReviewTool
from app.services.intake_review_workspace import (
    classify_intake_review_tool,
    hash_intake_review_identifier,
    mask_intake_review_identifier,
    sanitize_intake_review_value,
)


class AttachmentReviewError(ValueError):
    pass


URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(r"(?i)(?:bearer\s+\S+|(?:token|password|secret|client_secret)\s*[:=]\s*\S+)")
FILENAME = re.compile(r"(?i)\b[^\s/\\]+\.(?:pdf|png|jpe?g|gif|dwg|dxf|xlsx?|csv|docx?|zip|txt)\b")


def sanitize_attachment_review_value(value: Any) -> Any:
    return sanitize_intake_review_value(value)


def mask_attachment_review_identifier(value: Any) -> str | None:
    return mask_intake_review_identifier(value)


def hash_attachment_review_identifier(value: Any) -> str | None:
    return hash_intake_review_identifier(value)


def classify_attachment_file_category(
    metadata: AttachmentObject | dict[str, Any], settings: Settings
) -> AttachmentReviewFileCategory:
    content_type = (
        metadata.content_type
        if isinstance(metadata, AttachmentObject)
        else metadata.get("content_type")
    )
    normalized = str(content_type or "").casefold()
    if "blocked" in normalized or "quarantine" in normalized:
        return AttachmentReviewFileCategory.BLOCKED
    if normalized == "application/pdf":
        return AttachmentReviewFileCategory.PDF_LIKE
    if normalized.startswith("image/"):
        return AttachmentReviewFileCategory.IMAGE_LIKE
    if any(value in normalized for value in ("dwg", "dxf", "cad", "drawing")):
        return AttachmentReviewFileCategory.DRAWING_LIKE
    if any(value in normalized for value in ("spreadsheet", "excel", "csv")):
        return AttachmentReviewFileCategory.SPREADSHEET_LIKE
    if normalized.startswith("text/") or any(
        value in normalized for value in ("json", "xml", "word")
    ):
        return AttachmentReviewFileCategory.TEXT_LIKE
    if any(value in normalized for value in ("zip", "gzip", "tar", "archive")):
        return AttachmentReviewFileCategory.ARCHIVE_LIKE
    return AttachmentReviewFileCategory.UNKNOWN


def build_attachment_review_filter(
    settings: Settings,
    *,
    availability: str | AttachmentReviewAvailability | None = None,
    tool: str | IntakeReviewTool | None = None,
    storage_status: str | AttachmentReviewStorageStatus | None = None,
    page: int = 1,
    page_size: int | None = None,
    sort: str | AttachmentReviewSort | None = None,
) -> AttachmentReviewFilter:
    try:
        return AttachmentReviewFilter(
            availability=(AttachmentReviewAvailability(availability) if availability else None),
            tool=IntakeReviewTool(tool) if tool else None,
            storage_status=(
                AttachmentReviewStorageStatus(storage_status) if storage_status else None
            ),
            page=max(page, 1),
            page_size=min(
                max(page_size or settings.attachment_review_page_size, 1),
                settings.attachment_review_max_page_size,
            ),
            sort=AttachmentReviewSort(sort or settings.attachment_review_default_sort),
        )
    except ValueError as exc:
        raise AttachmentReviewError("Unsupported attachment review filter.") from exc


def _storage_status(row: AttachmentObject) -> AttachmentReviewStorageStatus:
    status = row.download_status.casefold()
    if status == "skipped":
        return AttachmentReviewStorageStatus.SKIPPED
    if status in {"blocked", "failed", "quarantined"}:
        return AttachmentReviewStorageStatus.BLOCKED
    if status == "downloaded":
        backend = row.storage_backend.casefold()
        if backend == "fixture":
            return AttachmentReviewStorageStatus.FIXTURE_METADATA_AVAILABLE
        if backend in {"s3", "azure_blob", "gcs", "cloud"}:
            return AttachmentReviewStorageStatus.CLOUD_METADATA_AVAILABLE
        return AttachmentReviewStorageStatus.LOCAL_METADATA_AVAILABLE
    if status == "planned":
        return AttachmentReviewStorageStatus.NOT_DOWNLOADED
    return AttachmentReviewStorageStatus.UNKNOWN


def _availability(row: AttachmentObject) -> AttachmentReviewAvailability:
    status = row.download_status.casefold()
    if status == "planned":
        return AttachmentReviewAvailability.ATTACHMENT_PLANNED
    if status == "downloaded":
        return AttachmentReviewAvailability.ATTACHMENT_STORED_METADATA_ONLY
    if status == "skipped":
        return AttachmentReviewAvailability.ATTACHMENT_SKIPPED
    if status in {"blocked", "failed", "quarantined"}:
        return AttachmentReviewAvailability.ATTACHMENT_BLOCKED
    return AttachmentReviewAvailability.UNKNOWN


def _checksum_status(row: AttachmentObject) -> AttachmentReviewChecksumStatus:
    if row.checksum_sha256:
        return AttachmentReviewChecksumStatus.CHECKSUM_PRESENT
    if row.download_status.casefold() in {"planned", "skipped", "blocked"}:
        return AttachmentReviewChecksumStatus.CHECKSUM_NOT_APPLICABLE
    if row.download_status.casefold() == "downloaded":
        return AttachmentReviewChecksumStatus.CHECKSUM_MISSING
    return AttachmentReviewChecksumStatus.UNKNOWN


def _safe_configuration(settings: Settings) -> bool:
    return not any(
        (
            settings.attachment_review_expose_source_urls,
            settings.attachment_review_expose_signed_urls,
            settings.attachment_review_expose_storage_keys,
            settings.attachment_review_expose_private_paths,
            settings.attachment_review_expose_original_filenames,
            settings.attachment_review_expose_contents,
        )
    )


def _attachment_rows(session: Session, record_id: int) -> list[AttachmentObject]:
    if not inspect(session.get_bind()).has_table(AttachmentObject.__tablename__):
        return []
    return list(
        session.scalars(
            select(AttachmentObject)
            .where(AttachmentObject.intake_record_id == record_id)
            .order_by(AttachmentObject.id)
        )
    )


def build_attachment_manifest_summary(
    record: IntakeRecord, session: Session, settings: Settings
) -> AttachmentReviewManifestSummary:
    if not settings.attachment_review_include_manifest_summary:
        return AttachmentReviewManifestSummary(
            availability=AttachmentReviewAvailability.UNKNOWN,
            planned_count=record.attachment_count or 0,
        )
    rows = _attachment_rows(session, record.id)
    categories: dict[AttachmentReviewFileCategory, int] = {}
    storage_statuses: dict[AttachmentReviewStorageStatus, int] = {}
    for row in rows:
        category = classify_attachment_file_category(row, settings)
        storage = _storage_status(row)
        categories[category] = categories.get(category, 0) + 1
        storage_statuses[storage] = storage_statuses.get(storage, 0) + 1
    return AttachmentReviewManifestSummary(
        availability=(
            AttachmentReviewAvailability.MANIFEST_PRESENT
            if rows
            else AttachmentReviewAvailability.MANIFEST_MISSING
        ),
        manifest_count=len(rows),
        planned_count=max(record.attachment_count or 0, len(rows)),
        stored_metadata_count=sum(row.download_status.casefold() == "downloaded" for row in rows),
        skipped_count=sum(row.download_status.casefold() == "skipped" for row in rows),
        blocked_count=sum(
            row.download_status.casefold() in {"blocked", "failed", "quarantined"} for row in rows
        ),
        size_known_count=sum(row.size_bytes is not None for row in rows),
        total_size_bytes=sum(row.size_bytes or 0 for row in rows),
        checksum_present_count=sum(bool(row.checksum_sha256) for row in rows),
        checksum_missing_count=sum(not row.checksum_sha256 for row in rows),
        source_available_count=sum(bool(row.source_url_present) for row in rows),
        file_categories=categories,
        storage_statuses=(
            storage_statuses if settings.attachment_review_include_storage_status else {}
        ),
    )


def _item(row: AttachmentObject, settings: Settings) -> AttachmentReviewItem:
    item = AttachmentReviewItem(
        attachment_id_masked=(
            mask_attachment_review_identifier(row.procore_attachment_id)
            if settings.attachment_review_mask_attachment_ids
            else None
        ),
        attachment_id_hash=(
            hash_attachment_review_identifier(row.procore_attachment_id)
            if settings.attachment_review_hash_attachment_ids
            else None
        ),
        availability=_availability(row),
        storage_status=(
            _storage_status(row)
            if settings.attachment_review_include_storage_status
            else AttachmentReviewStorageStatus.UNKNOWN
        ),
        checksum_status=(
            _checksum_status(row)
            if settings.attachment_review_include_checksum_status
            else AttachmentReviewChecksumStatus.UNKNOWN
        ),
        file_category=classify_attachment_file_category(row, settings),
        size_bytes=row.size_bytes,
        source_available=bool(row.source_url_present),
    )
    validate_attachment_review_response_safe(item)
    return item


def _record_summary(
    record: IntakeRecord, session: Session, settings: Settings
) -> AttachmentReviewRecordSummary:
    summary = AttachmentReviewRecordSummary(
        record_id=record.id,
        tool=classify_intake_review_tool(record.source_type),
        display_number=mask_attachment_review_identifier(record.number) or "••••",
        title=sanitize_attachment_review_value(record.title),
        received_at=record.received_at,
        manifest=build_attachment_manifest_summary(record, session, settings),
    )
    validate_attachment_review_response_safe(summary)
    return summary


def _record_summaries(session: Session, settings: Settings) -> list[AttachmentReviewRecordSummary]:
    if not inspect(session.get_bind()).has_table(IntakeRecord.__tablename__):
        return []
    return [
        _record_summary(record, session, settings)
        for record in session.scalars(select(IntakeRecord).order_by(IntakeRecord.id))
    ]


def _primary_storage_status(
    item: AttachmentReviewRecordSummary,
) -> AttachmentReviewStorageStatus:
    statuses = item.manifest.storage_statuses
    return (
        min(statuses, key=lambda status: status.value)
        if statuses
        else (AttachmentReviewStorageStatus.UNKNOWN)
    )


def _sort_records(
    items: list[AttachmentReviewRecordSummary], sort: AttachmentReviewSort
) -> list[AttachmentReviewRecordSummary]:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    by_id = sorted(items, key=lambda item: item.record_id)
    key, reverse = {
        AttachmentReviewSort.RECORD_RECEIVED_AT_DESC: (
            lambda item: item.received_at or epoch,
            True,
        ),
        AttachmentReviewSort.RECORD_RECEIVED_AT_ASC: (
            lambda item: item.received_at or epoch,
            False,
        ),
        AttachmentReviewSort.ATTACHMENT_COUNT_DESC: (
            lambda item: item.manifest.manifest_count,
            True,
        ),
        AttachmentReviewSort.ATTACHMENT_COUNT_ASC: (
            lambda item: item.manifest.manifest_count,
            False,
        ),
        AttachmentReviewSort.TOOL_ASC: (lambda item: item.tool.value, False),
        AttachmentReviewSort.TOOL_DESC: (lambda item: item.tool.value, True),
        AttachmentReviewSort.STORAGE_STATUS_ASC: (
            lambda item: _primary_storage_status(item).value,
            False,
        ),
        AttachmentReviewSort.STORAGE_STATUS_DESC: (
            lambda item: _primary_storage_status(item).value,
            True,
        ),
    }[sort]
    return sorted(by_id, key=key, reverse=reverse)


def list_attachment_review_records(
    session: Session, filters: AttachmentReviewFilter, settings: Settings
) -> AttachmentReviewPage:
    base = dict(
        page=filters.page,
        page_size=filters.page_size,
        total_items=0,
        total_pages=0,
        sort=filters.sort,
        availability_filter=filters.availability,
        tool_filter=filters.tool,
        storage_status_filter=filters.storage_status,
    )
    if not settings.attachment_review_enabled:
        return AttachmentReviewPage(status=AttachmentReviewStatus.DISABLED, **base)
    if settings.attachment_review_fail_closed and not _safe_configuration(settings):
        return AttachmentReviewPage(status=AttachmentReviewStatus.NEEDS_CONFIGURATION, **base)
    items = _record_summaries(session, settings)
    if filters.availability:
        if filters.availability in {
            AttachmentReviewAvailability.MANIFEST_PRESENT,
            AttachmentReviewAvailability.MANIFEST_MISSING,
        }:
            items = [item for item in items if item.manifest.availability is filters.availability]
        else:
            items = [
                item
                for item in items
                if any(
                    _availability(row) is filters.availability
                    for row in _attachment_rows(session, item.record_id)
                )
            ]
    if filters.tool:
        items = [item for item in items if item.tool is filters.tool]
    if filters.storage_status:
        items = [item for item in items if filters.storage_status in item.manifest.storage_statuses]
    items = _sort_records(items, filters.sort)
    total = len(items)
    start = (filters.page - 1) * filters.page_size
    page = AttachmentReviewPage(
        status=AttachmentReviewStatus.AVAILABLE if total else AttachmentReviewStatus.EMPTY,
        items=items[start : start + filters.page_size],
        page=filters.page,
        page_size=filters.page_size,
        total_items=total,
        total_pages=math.ceil(total / filters.page_size) if total else 0,
        sort=filters.sort,
        availability_filter=filters.availability,
        tool_filter=filters.tool,
        storage_status_filter=filters.storage_status,
    )
    validate_attachment_review_response_safe(page)
    return page


def get_attachment_review_record_detail(
    session: Session, record_id: int, settings: Settings
) -> AttachmentReviewRecordDetail | None:
    if not settings.attachment_review_enabled or not _safe_configuration(settings):
        return None
    record = session.get(IntakeRecord, record_id)
    if record is None:
        return None
    summary = _record_summary(record, session, settings)
    detail = AttachmentReviewRecordDetail(
        **summary.model_dump(),
        items=[_item(row, settings) for row in _attachment_rows(session, record.id)],
    )
    validate_attachment_review_response_safe(detail)
    return detail


def build_attachment_review_workspace_summary(
    session: Session, settings: Settings
) -> AttachmentReviewWorkspaceSummary:
    if not settings.attachment_review_enabled:
        return AttachmentReviewWorkspaceSummary(
            status=AttachmentReviewStatus.DISABLED,
            message="Attachment review is disabled.",
        )
    if settings.attachment_review_fail_closed and not _safe_configuration(settings):
        return AttachmentReviewWorkspaceSummary(
            status=AttachmentReviewStatus.NEEDS_CONFIGURATION,
            message="Attachment review requires safe metadata-only configuration.",
        )
    items = _record_summaries(session, settings)
    summary = AttachmentReviewWorkspaceSummary(
        status=AttachmentReviewStatus.AVAILABLE if items else AttachmentReviewStatus.EMPTY,
        total_records=len(items),
        records_with_manifests=sum(item.manifest.manifest_count > 0 for item in items),
        records_without_manifests=sum(item.manifest.manifest_count == 0 for item in items),
        planned_attachments=sum(item.manifest.planned_count for item in items),
        stored_metadata_attachments=sum(item.manifest.stored_metadata_count for item in items),
        skipped_attachments=sum(item.manifest.skipped_count for item in items),
        blocked_attachments=sum(item.manifest.blocked_count for item in items),
        message=(
            "Sanitized local attachment metadata is available."
            if items
            else "No local records yet; start with the safe Demo flow."
        ),
    )
    validate_attachment_review_response_safe(summary)
    return summary


def validate_attachment_review_response_safe(
    response: BaseModel | dict[str, Any],
) -> None:
    payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
    text = json.dumps(payload, default=str)
    keys = {str(key).casefold() for key in _walk_keys(payload)}
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
    }
    if (
        keys & forbidden_keys
        or URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
        or FILENAME.search(text)
    ):
        raise AttachmentReviewError("Unsafe attachment review response was blocked.")


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def render_attachment_review_markdown(
    summary_or_page: AttachmentReviewWorkspaceSummary | AttachmentReviewPage,
) -> str:
    if isinstance(summary_or_page, AttachmentReviewWorkspaceSummary):
        return "\n".join(
            [
                "# Attachment Review and Manifest UX",
                "",
                f"- Status: `{summary_or_page.status.value}`",
                f"- Local records: `{summary_or_page.total_records}`",
                f"- Records with manifests: `{summary_or_page.records_with_manifests}`",
                f"- Planned attachments: `{summary_or_page.planned_attachments}`",
                "- Metadata only: `true`",
                "- Contents available: `false`",
                "- Procore calls made: `false`",
                "- Storage calls made: `false`",
            ]
        )
    return "\n".join(
        [
            "# Attachment Review page",
            "",
            f"- Status: `{summary_or_page.status.value}`",
            f"- Records: `{len(summary_or_page.items)}`",
            f"- Page: `{summary_or_page.page}`",
            "- Metadata only: `true`",
        ]
    )
