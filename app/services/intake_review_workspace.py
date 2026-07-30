import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy import case, func, inspect, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.models.intake_lifecycle import IntakeReviewState
from app.models.intake_records import IntakeRecord
from app.models.sync_runs import SyncRun
from app.models.webhook_events import WebhookEvent
from app.schemas.intake_lifecycle import IntakeLifecycleStatus
from app.schemas.intake_review_workspace import (
    IntakeReviewAttachmentSummary,
    IntakeReviewFilter,
    IntakeReviewFinding,
    IntakeReviewPrioritySignal,
    IntakeReviewRecordDetail,
    IntakeReviewRecordListItem,
    IntakeReviewSort,
    IntakeReviewSourceContext,
    IntakeReviewTool,
    IntakeReviewWorkspacePage,
    IntakeReviewWorkspaceStatus,
    IntakeReviewWorkspaceSummary,
)
from app.services.intake_lifecycle import (
    get_lifecycle_state,
    list_lifecycle_history,
)


class IntakeReviewWorkspaceError(ValueError):
    pass


_URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
_PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\|private-workspace)")
_SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:token|password|secret|client_secret)\s*[:=]\s*\S+)"
)


def sanitize_intake_review_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): sanitize_intake_review_value(item)
            for key, item in value.items()
            if str(key).casefold()
            not in {"raw_payload", "raw_payload_json", "payload_json", "normalized_json"}
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_intake_review_value(item) for item in value]
    if isinstance(value, str):
        cleaned = _URL.sub("[redacted-url]", value)
        cleaned = _PRIVATE_PATH.sub("[redacted-path]", cleaned)
        return _SECRET.sub("[redacted-secret]", cleaned)[:500]
    return value


def mask_intake_review_identifier(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value)
    return f"••••{text[-4:]}" if len(text) > 4 else "••••"


def hash_intake_review_identifier(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def classify_intake_review_tool(source_type: str) -> IntakeReviewTool:
    normalized = source_type.casefold().rstrip("s")
    if normalized == "rfi":
        return IntakeReviewTool.RFI
    if normalized == "submittal":
        return IntakeReviewTool.SUBMITTAL
    return IntakeReviewTool.UNKNOWN


def build_intake_review_filter(
    settings: Settings,
    *,
    tool: str | IntakeReviewTool | None = None,
    page: int = 1,
    page_size: int | None = None,
    sort: str | IntakeReviewSort | None = None,
) -> IntakeReviewFilter:
    try:
        selected_tool = IntakeReviewTool(tool) if tool else None
        selected_sort = IntakeReviewSort(sort or settings.intake_review_workspace_default_sort)
    except ValueError as exc:
        raise IntakeReviewWorkspaceError("Unsupported intake review filter.") from exc
    bounded_size = min(
        max(page_size or settings.intake_review_workspace_page_size, 1),
        settings.intake_review_workspace_max_page_size,
    )
    return IntakeReviewFilter(
        tool=selected_tool, page=max(page, 1), page_size=bounded_size, sort=selected_sort
    )


def _sort_columns(sort: IntakeReviewSort):
    mapping = {
        IntakeReviewSort.RECEIVED_AT_DESC: (
            IntakeRecord.received_at.desc(),
            IntakeRecord.id.desc(),
        ),
        IntakeReviewSort.RECEIVED_AT_ASC: (
            IntakeRecord.received_at.asc(),
            IntakeRecord.id.asc(),
        ),
        IntakeReviewSort.UPDATED_AT_DESC: (
            IntakeRecord.updated_at.desc(),
            IntakeRecord.id.desc(),
        ),
        IntakeReviewSort.UPDATED_AT_ASC: (
            IntakeRecord.updated_at.asc(),
            IntakeRecord.id.asc(),
        ),
        IntakeReviewSort.TOOL_ASC: (
            IntakeRecord.source_type.asc(),
            IntakeRecord.id.asc(),
        ),
        IntakeReviewSort.TOOL_DESC: (
            IntakeRecord.source_type.desc(),
            IntakeRecord.id.desc(),
        ),
    }
    return mapping[sort]


def _workspace_table_available(session: Session) -> bool:
    return inspect(session.get_bind()).has_table(IntakeRecord.__tablename__)


def _unsafe_configuration(settings: Settings) -> bool:
    return (
        settings.intake_review_workspace_expose_raw_payloads
        or settings.intake_review_workspace_expose_private_paths
    )


def build_intake_review_attachment_summary(
    record: IntakeRecord, session: Session, settings: Settings
) -> IntakeReviewAttachmentSummary | None:
    if not settings.intake_review_workspace_include_attachment_summary:
        return None
    rows = list(
        session.scalars(
            select(AttachmentObject).where(AttachmentObject.intake_record_id == record.id)
        )
    )
    content_types: dict[str, int] = {}
    for row in rows:
        key = sanitize_intake_review_value(row.content_type or "unknown")
        content_types[key] = content_types.get(key, 0) + 1
    return IntakeReviewAttachmentSummary(
        manifest_count=len(rows),
        declared_count=max(record.attachment_count, len(record.attachments)),
        checksum_count=sum(bool(row.checksum_sha256) for row in rows),
        source_url_hash_count=sum(bool(row.source_url_hash) for row in rows),
        content_types=content_types,
    )


def build_intake_review_source_context(
    record: IntakeRecord, session: Session, settings: Settings
) -> IntakeReviewSourceContext | None:
    if not settings.intake_review_workspace_include_source_context:
        return None
    run = session.get(SyncRun, record.sync_run_id)
    event_count = session.scalar(
        select(func.count())
        .select_from(WebhookEvent)
        .where(
            WebhookEvent.procore_project_id == record.procore_project_id,
            WebhookEvent.procore_item_id == record.procore_item_id,
        )
    ) or 0
    return IntakeReviewSourceContext(
        project_id_masked=(
            mask_intake_review_identifier(record.procore_project_id)
            if settings.intake_review_workspace_mask_source_ids
            else None
        ),
        project_id_hash=(
            hash_intake_review_identifier(record.procore_project_id)
            if settings.intake_review_workspace_hash_source_ids
            else None
        ),
        item_id_masked=(
            mask_intake_review_identifier(record.procore_item_id)
            if settings.intake_review_workspace_mask_source_ids
            else None
        ),
        item_id_hash=(
            hash_intake_review_identifier(record.procore_item_id)
            if settings.intake_review_workspace_hash_source_ids
            else None
        ),
        sync_run_reference=f"local-sync-{record.sync_run_id}",
        sync_mode=sanitize_intake_review_value(run.mode) if run else None,
        sync_status=sanitize_intake_review_value(run.status) if run else None,
        matching_event_count=event_count,
    )


def build_intake_review_priority_signals(
    record: IntakeRecord,
    attachment_summary: IntakeReviewAttachmentSummary | None,
    source_context: IntakeReviewSourceContext | None,
    settings: Settings,
) -> list[IntakeReviewPrioritySignal]:
    signals = []
    has_manifest = bool(attachment_summary and attachment_summary.manifest_count)
    signals.append(
        IntakeReviewPrioritySignal(
            code="has_attachment_manifest" if has_manifest else "missing_attachment_manifest",
            label=(
                "Attachment manifest available"
                if has_manifest
                else "Attachment manifest missing"
            ),
        )
    )
    has_context = bool(
        source_context and (source_context.project_id_hash or source_context.item_id_hash)
    )
    signals.append(
        IntakeReviewPrioritySignal(
            code="source_context_available" if has_context else "source_context_missing",
            label="Source context available" if has_context else "Source context missing",
        )
    )
    received = record.received_at
    if received and received.tzinfo is None:
        received = received.replace(tzinfo=UTC)
    recent = bool(received and received >= datetime.now(UTC) - timedelta(days=7))
    signals.append(
        IntakeReviewPrioritySignal(
            code="recently_received" if recent else "older_record",
            label="Recently received" if recent else "Older record",
        )
    )
    signals.append(
        IntakeReviewPrioritySignal(
            code="needs_operator_review_placeholder",
            label="Operator review suggested (no lifecycle state)",
        )
    )
    return signals


def _item(record: IntakeRecord, session: Session, settings: Settings):
    attachments = build_intake_review_attachment_summary(record, session, settings)
    source = build_intake_review_source_context(record, session, settings)
    lifecycle_status = IntakeLifecycleStatus.NEW
    if inspect(session.get_bind()).has_table(IntakeReviewState.__tablename__):
        existing_state = session.scalar(
            select(IntakeReviewState).where(
                IntakeReviewState.intake_record_id == record.id
            )
        )
        if existing_state is not None:
            lifecycle_status = IntakeLifecycleStatus(existing_state.status)
    return IntakeReviewRecordListItem(
        record_id=record.id,
        tool=classify_intake_review_tool(record.source_type),
        display_number=mask_intake_review_identifier(record.number) or "••••",
        title=sanitize_intake_review_value(record.title),
        source_status=sanitize_intake_review_value(record.status),
        due_date=record.due_date,
        received_at=record.received_at,
        updated_at=record.updated_at,
        attachment_summary=attachments,
        source_context=source,
        priority_signals=build_intake_review_priority_signals(
            record, attachments, source, settings
        ),
        lifecycle_status=lifecycle_status,
    )


def list_intake_review_records(
    session: Session, filters: IntakeReviewFilter, settings: Settings
) -> IntakeReviewWorkspacePage:
    if not settings.intake_review_workspace_enabled:
        return IntakeReviewWorkspacePage(
            status=IntakeReviewWorkspaceStatus.DISABLED,
            page=filters.page,
            page_size=filters.page_size,
            total_items=0,
            total_pages=0,
            sort=filters.sort,
            tool_filter=filters.tool,
        )
    if _unsafe_configuration(settings):
        return IntakeReviewWorkspacePage(
            status=IntakeReviewWorkspaceStatus.NEEDS_CONFIGURATION,
            page=filters.page,
            page_size=filters.page_size,
            total_items=0,
            total_pages=0,
            sort=filters.sort,
            tool_filter=filters.tool,
        )
    if not _workspace_table_available(session):
        return IntakeReviewWorkspacePage(
            status=IntakeReviewWorkspaceStatus.EMPTY,
            page=filters.page,
            page_size=filters.page_size,
            total_items=0,
            total_pages=0,
            sort=filters.sort,
            tool_filter=filters.tool,
        )
    statement = select(IntakeRecord)
    count_statement = select(func.count()).select_from(IntakeRecord)
    if filters.tool:
        variants = {
            IntakeReviewTool.RFI: ("rfi", "rfis"),
            IntakeReviewTool.SUBMITTAL: ("submittal", "submittals"),
            IntakeReviewTool.UNKNOWN: (),
        }
        if filters.tool is IntakeReviewTool.UNKNOWN:
            known = ("rfi", "rfis", "submittal", "submittals")
            statement = statement.where(func.lower(IntakeRecord.source_type).not_in(known))
            count_statement = count_statement.where(
                func.lower(IntakeRecord.source_type).not_in(known)
            )
        else:
            statement = statement.where(
                func.lower(IntakeRecord.source_type).in_(variants[filters.tool])
            )
            count_statement = count_statement.where(
                func.lower(IntakeRecord.source_type).in_(variants[filters.tool])
            )
    total = session.scalar(count_statement) or 0
    rows = session.scalars(
        statement.order_by(*_sort_columns(filters.sort))
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    page = IntakeReviewWorkspacePage(
        status=(
            IntakeReviewWorkspaceStatus.AVAILABLE
            if total
            else IntakeReviewWorkspaceStatus.EMPTY
        ),
        items=[_item(row, session, settings) for row in rows],
        page=filters.page,
        page_size=filters.page_size,
        total_items=total,
        total_pages=math.ceil(total / filters.page_size) if total else 0,
        sort=filters.sort,
        tool_filter=filters.tool,
    )
    validate_intake_review_response_safe(page)
    return page


def get_intake_review_record_detail(
    session: Session, record_id: int, settings: Settings
) -> IntakeReviewRecordDetail | None:
    if not settings.intake_review_workspace_enabled:
        raise IntakeReviewWorkspaceError("Intake Review Workspace is disabled.")
    if _unsafe_configuration(settings):
        raise IntakeReviewWorkspaceError(
            "Unsafe Intake Review Workspace exposure settings were blocked."
        )
    if not _workspace_table_available(session):
        return None
    record = session.get(IntakeRecord, record_id)
    if record is None:
        return None
    item = _item(record, session, settings)
    lifecycle_state = get_lifecycle_state(session, record.id, settings)
    lifecycle_history = list_lifecycle_history(
        session, record.id, 1, 10, settings
    )
    detail_values = item.model_dump()
    detail_values["lifecycle_status"] = lifecycle_state.status
    detail = IntakeReviewRecordDetail(
        **detail_values,
        findings=[
            IntakeReviewFinding(
                code="local_lifecycle_only",
                message="Lifecycle changes remain local and never write to Procore.",
            )
        ],
        lifecycle_state=lifecycle_state,
        recent_lifecycle_history=lifecycle_history.items,
    )
    validate_intake_review_response_safe(detail)
    return detail


def build_intake_review_workspace_summary(
    session: Session, settings: Settings
) -> IntakeReviewWorkspaceSummary:
    if not settings.intake_review_workspace_enabled:
        return IntakeReviewWorkspaceSummary(
            status=IntakeReviewWorkspaceStatus.DISABLED,
            message="The local Intake Review Workspace is disabled.",
        )
    if _unsafe_configuration(settings):
        return IntakeReviewWorkspaceSummary(
            status=IntakeReviewWorkspaceStatus.NEEDS_CONFIGURATION,
            message="Unsafe workspace exposure settings were blocked; restore safe defaults.",
        )
    if not _workspace_table_available(session):
        return IntakeReviewWorkspaceSummary(
            status=IntakeReviewWorkspaceStatus.EMPTY,
            message=(
                "No local database tables yet. Start with `make try-demo`; fixture persistence "
                "is a separate explicit local step."
            ),
        )
    tool_group = case(
        (func.lower(IntakeRecord.source_type).in_(("rfi", "rfis")), "rfi"),
        (
            func.lower(IntakeRecord.source_type).in_(("submittal", "submittals")),
            "submittal",
        ),
        else_="unknown",
    )
    counts = dict(
        session.execute(
            select(tool_group, func.count()).group_by(tool_group)
        ).all()
    )
    total = sum(counts.values())
    manifested = session.scalar(
        select(func.count(func.distinct(AttachmentObject.intake_record_id))).where(
            AttachmentObject.intake_record_id.is_not(None)
        )
    ) or 0
    summary = IntakeReviewWorkspaceSummary(
        status=(
            IntakeReviewWorkspaceStatus.AVAILABLE
            if total
            else IntakeReviewWorkspaceStatus.EMPTY
        ),
        total_records=total,
        rfi_records=counts.get("rfi", 0),
        submittal_records=counts.get("submittal", 0),
        unknown_records=counts.get("unknown", 0),
        records_with_manifests=manifested,
        message=(
            "Local intake records are available for read-only review."
            if total
            else (
                "No local intake records yet. Start with `make try-demo`; fixture persistence "
                "is a separate explicit local step."
            )
        ),
        lifecycle_transitions_available=settings.intake_lifecycle_enabled,
    )
    validate_intake_review_response_safe(summary)
    return summary


def validate_intake_review_response_safe(response: BaseModel | dict[str, Any]) -> None:
    payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
    lowered_keys = {str(key).casefold() for key in _walk_keys(payload)}
    forbidden_keys = {
        "raw_payload",
        "raw_payload_json",
        "payload_json",
        "source_url",
        "source_url_redacted",
        "signed_url",
        "storage_path",
        "storage_key",
        "procore_project_id",
        "procore_item_id",
    }
    text = json.dumps(payload, default=str)
    if (
        lowered_keys & forbidden_keys
        or _URL.search(text)
        or _PRIVATE_PATH.search(text)
        or _SECRET.search(text)
    ):
        raise IntakeReviewWorkspaceError("Unsafe intake review response was blocked.")


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def render_intake_review_workspace_markdown(
    summary_or_page: IntakeReviewWorkspaceSummary | IntakeReviewWorkspacePage,
) -> str:
    if isinstance(summary_or_page, IntakeReviewWorkspaceSummary):
        return "\n".join(
            [
                "# Intake Review Workspace",
                "",
                f"- Status: `{summary_or_page.status.value}`",
                f"- Local records: `{summary_or_page.total_records}`",
                f"- RFI records: `{summary_or_page.rfi_records}`",
                f"- Submittal records: `{summary_or_page.submittal_records}`",
                f"- Message: {summary_or_page.message}",
                "- Read-only: `true`",
                "- Procore calls made: `false`",
            ]
        )
    return "\n".join(
        [
            "# Intake Review Workspace page",
            "",
            f"- Status: `{summary_or_page.status.value}`",
            f"- Page: `{summary_or_page.page}`",
            f"- Page size: `{summary_or_page.page_size}`",
            f"- Total local records: `{summary_or_page.total_items}`",
            "- Read-only: `true`",
        ]
    )
