import json
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.intake_lifecycle import IntakeReviewState
from app.models.intake_records import IntakeRecord
from app.schemas.intake_lifecycle import IntakeLifecycleStatus
from app.schemas.intake_review_workspace import IntakeReviewTool
from app.schemas.operator_triage_queue import (
    OperatorTriageBucket,
    OperatorTriageBucketSummary,
    OperatorTriageFilter,
    OperatorTriageQueueItem,
    OperatorTriageQueuePage,
    OperatorTriageQueueSummary,
    OperatorTriageSignal,
    OperatorTriageSort,
    OperatorTriageStatus,
)
from app.services.intake_review_workspace import (
    build_intake_review_attachment_summary,
    build_intake_review_source_context,
    classify_intake_review_tool,
    hash_intake_review_identifier,
    mask_intake_review_identifier,
    sanitize_intake_review_value,
)


class OperatorTriageQueueError(ValueError):
    pass


URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\|private-workspace)")
SECRET = re.compile(r"(?i)(?:bearer\s+\S+|(?:token|password|secret|client_secret)\s*[:=]\s*\S+)")


def sanitize_triage_value(value: Any) -> Any:
    return sanitize_intake_review_value(value)


def mask_triage_identifier(value: Any) -> str | None:
    return mask_intake_review_identifier(value)


def hash_triage_identifier(value: Any) -> str | None:
    return hash_intake_review_identifier(value)


def build_operator_triage_filter(
    settings: Settings,
    *,
    bucket: str | OperatorTriageBucket | None = None,
    tool: str | IntakeReviewTool | None = None,
    lifecycle_status: str | IntakeLifecycleStatus | None = None,
    page: int = 1,
    page_size: int | None = None,
    sort: str | OperatorTriageSort | None = None,
) -> OperatorTriageFilter:
    try:
        return OperatorTriageFilter(
            bucket=OperatorTriageBucket(bucket) if bucket else None,
            tool=IntakeReviewTool(tool) if tool else None,
            lifecycle_status=(
                IntakeLifecycleStatus(lifecycle_status) if lifecycle_status else None
            ),
            page=max(page, 1),
            page_size=min(
                max(page_size or settings.triage_queue_page_size, 1),
                settings.triage_queue_max_page_size,
            ),
            sort=OperatorTriageSort(sort or settings.triage_queue_default_sort),
        )
    except ValueError as exc:
        raise OperatorTriageQueueError("Unsupported triage filter.") from exc


def compute_triage_signals(
    record: IntakeRecord,
    lifecycle_state: IntakeReviewState | None,
    attachment_summary,
    source_context,
    settings: Settings,
) -> list[OperatorTriageSignal]:
    status = IntakeLifecycleStatus(
        lifecycle_state.status if lifecycle_state else IntakeLifecycleStatus.NEW
    )
    signals: list[OperatorTriageSignal] = []
    lifecycle = {
        IntakeLifecycleStatus.NEEDS_FOLLOW_UP: (
            "lifecycle_needs_follow_up",
            "Needs local follow-up",
            50,
        ),
        IntakeLifecycleStatus.NEW: ("lifecycle_new", "New local record", 30),
        IntakeLifecycleStatus.IN_REVIEW: (
            "lifecycle_in_review",
            "Local review in progress",
            20,
        ),
        IntakeLifecycleStatus.REVIEWED: (
            "lifecycle_reviewed",
            "Locally reviewed",
            -20,
        ),
        IntakeLifecycleStatus.IGNORED: ("lifecycle_ignored", "Locally ignored", -30),
    }
    if settings.triage_queue_include_lifecycle:
        code, label, weight = lifecycle[status]
        signals.append(OperatorTriageSignal(code=code, label=label, weight=weight))
    received = record.received_at
    if received and received.tzinfo is None:
        received = received.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    unreviewed = status in {
        IntakeLifecycleStatus.NEW,
        IntakeLifecycleStatus.IN_REVIEW,
        IntakeLifecycleStatus.NEEDS_FOLLOW_UP,
    }
    if received and received >= now - timedelta(hours=settings.triage_queue_recent_hours):
        signals.append(
            OperatorTriageSignal(code="recently_received", label="Recently received", weight=10)
        )
    if (
        unreviewed
        and received
        and received < now - timedelta(hours=settings.triage_queue_older_than_hours)
    ):
        signals.append(
            OperatorTriageSignal(
                code="older_unreviewed", label="Older unreviewed record", weight=25
            )
        )
    if settings.triage_queue_include_attachment_signals:
        has_manifest = bool(attachment_summary and attachment_summary.manifest_count)
        signals.append(
            OperatorTriageSignal(
                code=("has_attachment_manifest" if has_manifest else "missing_attachment_manifest"),
                label=(
                    "Attachment manifest available"
                    if has_manifest
                    else "Attachment manifest missing"
                ),
                weight=5 if has_manifest else 10,
            )
        )
    if settings.triage_queue_include_source_context_signals:
        has_context = bool(
            source_context and (source_context.item_id_hash or source_context.project_id_hash)
        )
        signals.append(
            OperatorTriageSignal(
                code=("source_context_available" if has_context else "source_context_missing"),
                label="Source context available" if has_context else "Source context missing",
                weight=0 if has_context else 15,
            )
        )
    if classify_intake_review_tool(record.source_type) is IntakeReviewTool.UNKNOWN:
        signals.append(
            OperatorTriageSignal(code="unknown_tool", label="Unknown local source type", weight=20)
        )
    signals.append(
        OperatorTriageSignal(
            code="demo_placeholder_triage",
            label="Deterministic local triage",
            weight=0,
        )
    )
    return signals


def compute_triage_priority_score(signals: list[OperatorTriageSignal], settings: Settings) -> int:
    return sum(signal.weight for signal in signals)


def assign_triage_buckets(
    signals: list[OperatorTriageSignal],
    lifecycle_state: IntakeReviewState | None,
    settings: Settings,
) -> list[OperatorTriageBucket]:
    codes = {signal.code for signal in signals}
    mapping = {
        "lifecycle_needs_follow_up": OperatorTriageBucket.NEEDS_FOLLOW_UP,
        "lifecycle_new": OperatorTriageBucket.NEW_UNREVIEWED,
        "lifecycle_in_review": OperatorTriageBucket.IN_REVIEW,
        "older_unreviewed": OperatorTriageBucket.OLDER_UNREVIEWED,
        "recently_received": OperatorTriageBucket.RECENTLY_RECEIVED,
        "has_attachment_manifest": OperatorTriageBucket.HAS_ATTACHMENTS,
        "source_context_missing": OperatorTriageBucket.MISSING_SOURCE_CONTEXT,
        "unknown_tool": OperatorTriageBucket.UNKNOWN_TOOL,
        "lifecycle_reviewed": OperatorTriageBucket.REVIEWED,
        "lifecycle_ignored": OperatorTriageBucket.IGNORED,
    }
    return [bucket for code, bucket in mapping.items() if code in codes]


def _safe_configuration(settings: Settings) -> bool:
    return not (
        settings.triage_queue_expose_raw_payloads or settings.triage_queue_expose_private_paths
    )


def _build_items(session: Session, settings: Settings) -> list[OperatorTriageQueueItem]:
    states = {}
    if inspect(session.get_bind()).has_table(IntakeReviewState.__tablename__):
        states = {
            state.intake_record_id: state for state in session.scalars(select(IntakeReviewState))
        }
    items = []
    for record in session.scalars(select(IntakeRecord).order_by(IntakeRecord.id)):
        state = states.get(record.id)
        lifecycle_status = IntakeLifecycleStatus(
            state.status if state else IntakeLifecycleStatus.NEW
        )
        attachments = build_intake_review_attachment_summary(record, session, settings)
        source = build_intake_review_source_context(record, session, settings)
        signals = compute_triage_signals(record, state, attachments, source, settings)
        item = OperatorTriageQueueItem(
            record_id=record.id,
            tool=classify_intake_review_tool(record.source_type),
            display_number=mask_triage_identifier(record.number) or "••••",
            title=sanitize_triage_value(record.title),
            lifecycle_status=lifecycle_status,
            received_at=record.received_at,
            updated_at=record.updated_at,
            source_id_masked=(
                mask_triage_identifier(record.procore_item_id)
                if settings.triage_queue_mask_source_ids
                else None
            ),
            source_id_hash=(
                hash_triage_identifier(record.procore_item_id)
                if settings.triage_queue_hash_source_ids
                else None
            ),
            attachment_manifest_count=(attachments.manifest_count if attachments else 0),
            signals=signals,
            buckets=assign_triage_buckets(signals, state, settings),
            priority_score=compute_triage_priority_score(signals, settings),
        )
        validate_operator_triage_response_safe(item)
        items.append(item)
    return items


def _sort_items(items: list[OperatorTriageQueueItem], sort: OperatorTriageSort):
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    key = {
        OperatorTriageSort.PRIORITY_DESC: lambda item: (-item.priority_score, item.record_id),
        OperatorTriageSort.PRIORITY_ASC: lambda item: (item.priority_score, item.record_id),
        OperatorTriageSort.RECEIVED_AT_DESC: lambda item: (
            -(item.received_at or epoch).timestamp(),
            item.record_id,
        ),
        OperatorTriageSort.RECEIVED_AT_ASC: lambda item: (
            (item.received_at or epoch).timestamp(),
            item.record_id,
        ),
        OperatorTriageSort.LIFECYCLE_STATUS_ASC: lambda item: (
            item.lifecycle_status.value,
            item.record_id,
        ),
        OperatorTriageSort.LIFECYCLE_STATUS_DESC: lambda item: (
            "".join(chr(255 - ord(char)) for char in item.lifecycle_status.value),
            item.record_id,
        ),
        OperatorTriageSort.TOOL_ASC: lambda item: (item.tool.value, item.record_id),
        OperatorTriageSort.TOOL_DESC: lambda item: (
            "".join(chr(255 - ord(char)) for char in item.tool.value),
            item.record_id,
        ),
    }[sort]
    return sorted(items, key=key)


def list_operator_triage_queue(
    session: Session, filters: OperatorTriageFilter, settings: Settings
) -> OperatorTriageQueuePage:
    base = dict(
        page=filters.page,
        page_size=filters.page_size,
        total_items=0,
        total_pages=0,
        sort=filters.sort,
        bucket_filter=filters.bucket,
        tool_filter=filters.tool,
        lifecycle_filter=filters.lifecycle_status,
    )
    if not settings.triage_queue_enabled:
        return OperatorTriageQueuePage(status=OperatorTriageStatus.DISABLED, **base)
    if settings.triage_queue_fail_closed and not _safe_configuration(settings):
        return OperatorTriageQueuePage(status=OperatorTriageStatus.NEEDS_CONFIGURATION, **base)
    if not inspect(session.get_bind()).has_table(IntakeRecord.__tablename__):
        return OperatorTriageQueuePage(status=OperatorTriageStatus.EMPTY, **base)
    items = _build_items(session, settings)
    if filters.bucket:
        items = [item for item in items if filters.bucket in item.buckets]
    if filters.tool:
        items = [item for item in items if item.tool is filters.tool]
    if filters.lifecycle_status:
        items = [item for item in items if item.lifecycle_status is filters.lifecycle_status]
    items = _sort_items(items, filters.sort)
    total = len(items)
    start = (filters.page - 1) * filters.page_size
    result = OperatorTriageQueuePage(
        status=OperatorTriageStatus.AVAILABLE if total else OperatorTriageStatus.EMPTY,
        items=items[start : start + filters.page_size],
        page=filters.page,
        page_size=filters.page_size,
        total_items=total,
        total_pages=math.ceil(total / filters.page_size) if total else 0,
        sort=filters.sort,
        bucket_filter=filters.bucket,
        tool_filter=filters.tool,
        lifecycle_filter=filters.lifecycle_status,
    )
    validate_operator_triage_response_safe(result)
    return result


def build_operator_triage_summary(
    session: Session, settings: Settings
) -> OperatorTriageQueueSummary:
    filters = build_operator_triage_filter(settings, page_size=settings.triage_queue_max_page_size)
    page = list_operator_triage_queue(session, filters, settings)
    if page.status in {
        OperatorTriageStatus.DISABLED,
        OperatorTriageStatus.NEEDS_CONFIGURATION,
    }:
        return OperatorTriageQueueSummary(
            status=page.status, message="Operator Triage Queue is unavailable."
        )
    all_items = (
        _build_items(session, settings) if page.status is not OperatorTriageStatus.EMPTY else []
    )
    bucket_counts = {
        bucket: sum(bucket in item.buckets for item in all_items) for bucket in OperatorTriageBucket
    }
    lifecycle = {
        status: sum(item.lifecycle_status is status for item in all_items)
        for status in IntakeLifecycleStatus
    }
    summary = OperatorTriageQueueSummary(
        status=OperatorTriageStatus.AVAILABLE if all_items else OperatorTriageStatus.EMPTY,
        total_records=len(all_items),
        buckets=[
            OperatorTriageBucketSummary(bucket=bucket, count=count)
            for bucket, count in bucket_counts.items()
        ],
        lifecycle_distribution=lifecycle,
        message=(
            "Sanitized local triage data is available."
            if all_items
            else "No local records yet; start with the safe Demo flow."
        ),
    )
    validate_operator_triage_response_safe(summary)
    return summary


def validate_operator_triage_response_safe(
    response: BaseModel | dict[str, Any],
) -> None:
    payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
    text = json.dumps(payload, default=str)
    keys = {str(key).casefold() for key in _walk_keys(payload)}
    forbidden_keys = {
        "raw_payload",
        "raw_payload_json",
        "payload_json",
        "source_url",
        "signed_url",
        "storage_path",
        "storage_key",
        "procore_project_id",
        "procore_item_id",
    }
    if (
        keys & forbidden_keys
        or URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
    ):
        raise OperatorTriageQueueError("Unsafe operator triage response was blocked.")


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def render_operator_triage_queue_markdown(
    summary_or_page: OperatorTriageQueueSummary | OperatorTriageQueuePage,
) -> str:
    if isinstance(summary_or_page, OperatorTriageQueueSummary):
        return "\n".join(
            [
                "# Operator Triage Queue",
                "",
                f"- Status: `{summary_or_page.status.value}`",
                f"- Local records: `{summary_or_page.total_records}`",
                f"- Description: {summary_or_page.priority_description}",
                "- Read-only: `true`",
                "- Procore calls made: `false`",
            ]
        )
    return "\n".join(
        [
            "# Operator Triage Queue page",
            "",
            f"- Status: `{summary_or_page.status.value}`",
            f"- Items: `{len(summary_or_page.items)}`",
            f"- Page: `{summary_or_page.page}`",
            "- Read-only: `true`",
        ]
    )
