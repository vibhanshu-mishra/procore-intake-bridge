import hashlib
import json
import math
import re
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.intake_lifecycle import (
    IntakeReviewLifecycleEvent,
    IntakeReviewState,
)
from app.models.intake_records import IntakeRecord
from app.schemas.intake_lifecycle import (
    IntakeLifecycleEventItem,
    IntakeLifecycleHistoryPage,
    IntakeLifecycleReasonCode,
    IntakeLifecycleStateView,
    IntakeLifecycleStatus,
    IntakeLifecycleSummary,
    IntakeLifecycleTransitionRequest,
    IntakeLifecycleTransitionResult,
)


class IntakeLifecycleError(ValueError):
    pass


class IntakeLifecycleBlockedError(IntakeLifecycleError):
    pass


# H4 defines the canonical local lifecycle vocabulary.  The Demo seed that
# predates that vocabulary used ``blocked`` and ``completed``; keep the
# explicit mappings here so old local rows can be read and repaired without
# expanding the public enum.
LEGACY_LIFECYCLE_STATUS_MAP = {
    "blocked": IntakeLifecycleStatus.NEEDS_FOLLOW_UP,
    "completed": IntakeLifecycleStatus.REVIEWED,
}
LEGACY_LIFECYCLE_REASON_CODE_MAP = {
    "j2_demo_fixture": IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON,
}


ALLOWED_TRANSITIONS = {
    IntakeLifecycleStatus.NEW: {
        IntakeLifecycleStatus.IN_REVIEW,
        IntakeLifecycleStatus.REVIEWED,
        IntakeLifecycleStatus.NEEDS_FOLLOW_UP,
        IntakeLifecycleStatus.IGNORED,
    },
    IntakeLifecycleStatus.IN_REVIEW: {
        IntakeLifecycleStatus.REVIEWED,
        IntakeLifecycleStatus.NEEDS_FOLLOW_UP,
        IntakeLifecycleStatus.IGNORED,
    },
    IntakeLifecycleStatus.REVIEWED: {
        IntakeLifecycleStatus.IN_REVIEW,
        IntakeLifecycleStatus.NEEDS_FOLLOW_UP,
    },
    IntakeLifecycleStatus.NEEDS_FOLLOW_UP: {
        IntakeLifecycleStatus.IN_REVIEW,
        IntakeLifecycleStatus.REVIEWED,
        IntakeLifecycleStatus.IGNORED,
    },
    IntakeLifecycleStatus.IGNORED: {IntakeLifecycleStatus.IN_REVIEW},
}
REASON_SUMMARIES = {
    IntakeLifecycleReasonCode.INITIAL_REVIEW_STARTED: "Initial local review started.",
    IntakeLifecycleReasonCode.REVIEWED_NO_ACTION_NEEDED: "Local review completed; no action noted.",
    IntakeLifecycleReasonCode.FOLLOW_UP_NEEDED: "Local follow-up is needed.",
    IntakeLifecycleReasonCode.DUPLICATE_OR_IRRELEVANT: "Marked duplicate or irrelevant locally.",
    IntakeLifecycleReasonCode.REOPENED_FOR_REVIEW: "Reopened for local review.",
    IntakeLifecycleReasonCode.MARKED_IN_ERROR: "Prior local status was marked in error.",
    IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON: "Synthetic Demo reason.",
}
FORBIDDEN = re.compile(
    r"(?i)\b(?:approv(?:e|ed|al)|reject(?:ed|ion)?|compliance(?:_|\s)*(?:passed|failed)|"
    r"sent(?:_|\s)*to(?:_|\s)*(?:procore|customer)|assign(?:ed|ment)?|commented|notified)\b"
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\|private-workspace)")
SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:token|password|secret|client_secret)\s*[:=]\s*\S+)"
)


def _raw_lifecycle_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().casefold()


def normalize_lifecycle_status(value: Any) -> tuple[IntakeLifecycleStatus, str | None]:
    """Return a safe canonical status and a non-sensitive normalization code.

    ``legacy_status_normalized`` identifies one of the documented legacy
    labels.  ``unknown_status_needs_review`` is a fail-safe representation for
    an unexpected stored value; the raw value is never returned.
    """

    raw = _raw_lifecycle_value(value)
    try:
        return IntakeLifecycleStatus(raw), None
    except ValueError:
        mapped = LEGACY_LIFECYCLE_STATUS_MAP.get(raw)
        if mapped is not None:
            return mapped, "legacy_status_normalized"
        return IntakeLifecycleStatus.NEEDS_FOLLOW_UP, "unknown_status_needs_review"


def normalize_lifecycle_reason_code(value: Any) -> IntakeLifecycleReasonCode | None:
    """Return a canonical reason code without exposing unknown stored text."""

    raw = _raw_lifecycle_value(value)
    if not raw:
        return None
    try:
        return IntakeLifecycleReasonCode(raw)
    except ValueError:
        return LEGACY_LIFECYCLE_REASON_CODE_MAP.get(
            raw, IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON
        )


def normalize_legacy_lifecycle_data(
    session: Session, intake_record_ids: list[int] | None = None
) -> int:
    """Repair known legacy lifecycle labels in-place and return changed rows.

    This is deliberately allow-listed: only the documented Demo-era labels
    are changed.  Unknown values remain available for safe read-time
    needs-review handling and are never printed.
    """

    if not _tables_available(session):
        return 0
    state_query = select(IntakeReviewState)
    event_query = select(IntakeReviewLifecycleEvent)
    if intake_record_ids is not None:
        state_query = state_query.where(
            IntakeReviewState.intake_record_id.in_(intake_record_ids)
        )
        event_query = event_query.where(
            IntakeReviewLifecycleEvent.intake_record_id.in_(intake_record_ids)
        )
    changed = 0
    for state in session.scalars(state_query):
        raw_status = _raw_lifecycle_value(state.status)
        mapped_status = LEGACY_LIFECYCLE_STATUS_MAP.get(raw_status)
        if mapped_status is not None and state.status != mapped_status.value:
            state.status = mapped_status.value
            changed += 1
        raw_reason = _raw_lifecycle_value(state.current_reason_code)
        mapped_reason = LEGACY_LIFECYCLE_REASON_CODE_MAP.get(raw_reason)
        if mapped_reason is not None and state.current_reason_code != mapped_reason.value:
            state.current_reason_code = mapped_reason.value
            changed += 1
    for event in session.scalars(event_query):
        for attribute in ("from_status", "to_status"):
            raw_status = _raw_lifecycle_value(getattr(event, attribute))
            mapped_status = LEGACY_LIFECYCLE_STATUS_MAP.get(raw_status)
            if mapped_status is not None and getattr(event, attribute) != mapped_status.value:
                setattr(event, attribute, mapped_status.value)
                changed += 1
        raw_reason = _raw_lifecycle_value(event.reason_code)
        mapped_reason = LEGACY_LIFECYCLE_REASON_CODE_MAP.get(raw_reason)
        if mapped_reason is not None and event.reason_code != mapped_reason.value:
            event.reason_code = mapped_reason.value
            changed += 1
    if changed:
        session.flush()
    return changed


def sanitize_lifecycle_value(value: Any) -> str:
    text = str(value or "").strip()
    text = URL.sub("[redacted-url]", text)
    text = PRIVATE_PATH.sub("[redacted-path]", text)
    text = SECRET.sub("[redacted-secret]", text)
    return " ".join(text.split())


def mask_lifecycle_actor(value: Any) -> str | None:
    text = sanitize_lifecycle_value(value)
    if not text:
        return None
    return f"local-actor-••••{text[-4:]}" if len(text) > 4 else "local-actor-••••"


def hash_lifecycle_actor(value: Any) -> str | None:
    text = sanitize_lifecycle_value(value)
    return hashlib.sha256(text.encode()).hexdigest()[:12] if text else None


def _tables_available(session: Session) -> bool:
    inspector = inspect(session.get_bind())
    return all(
        inspector.has_table(name)
        for name in (
            IntakeRecord.__tablename__,
            IntakeReviewState.__tablename__,
            IntakeReviewLifecycleEvent.__tablename__,
        )
    )


def _safe_configuration(settings: Settings) -> bool:
    return not (
        settings.intake_lifecycle_expose_raw_payloads
        or settings.intake_lifecycle_expose_source_ids
        or settings.intake_lifecycle_expose_private_paths
    )


def _ensure_enabled(settings: Settings) -> None:
    if not settings.intake_lifecycle_enabled:
        raise IntakeLifecycleBlockedError("Local intake lifecycle is disabled.")
    if settings.intake_lifecycle_fail_closed and not _safe_configuration(settings):
        raise IntakeLifecycleBlockedError(
            "Unsafe lifecycle exposure settings were blocked."
        )


def _state_view(state: IntakeReviewState) -> IntakeLifecycleStateView:
    status, _ = normalize_lifecycle_status(state.status)
    return IntakeLifecycleStateView(
        intake_record_id=state.intake_record_id,
        status=status,
        current_reason_code=normalize_lifecycle_reason_code(state.current_reason_code),
        current_reason_summary_sanitized=(
            sanitize_lifecycle_value(state.current_reason_summary_sanitized)
            if state.current_reason_summary_sanitized
            else None
        ),
        actor_hash=state.actor_hash,
        actor_label_masked=state.actor_label_masked,
        event_count=state.event_count,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _event_item(event: IntakeReviewLifecycleEvent) -> IntakeLifecycleEventItem:
    from_status, _ = normalize_lifecycle_status(event.from_status)
    to_status, _ = normalize_lifecycle_status(event.to_status)
    return IntakeLifecycleEventItem(
        event_id=event.id,
        from_status=from_status,
        to_status=to_status,
        reason_code=(
            normalize_lifecycle_reason_code(event.reason_code)
            or IntakeLifecycleReasonCode.DEMO_PLACEHOLDER_REASON
        ),
        reason_summary_sanitized=sanitize_lifecycle_value(
            event.reason_summary_sanitized
        ),
        actor_hash=event.actor_hash,
        actor_label_masked=event.actor_label_masked,
        request_id_hash=event.request_id_hash,
        source=sanitize_lifecycle_value(event.source),
        created_at=event.created_at,
    )


def get_or_create_lifecycle_state(
    session: Session, intake_record_id: int, settings: Settings
) -> IntakeReviewState:
    _ensure_enabled(settings)
    if not _tables_available(session):
        raise IntakeLifecycleBlockedError("Local lifecycle tables are not initialized.")
    if session.get(IntakeRecord, intake_record_id) is None:
        raise IntakeLifecycleError("Local intake record not found.")
    state = session.scalar(
        select(IntakeReviewState).where(
            IntakeReviewState.intake_record_id == intake_record_id
        )
    )
    if state is None:
        state = IntakeReviewState(
            intake_record_id=intake_record_id,
            status=settings.intake_lifecycle_default_status,
        )
        session.add(state)
        session.flush()
    else:
        normalized_status, _ = normalize_lifecycle_status(state.status)
        if state.status != normalized_status.value:
            state.status = normalized_status.value
        normalize_legacy_lifecycle_data(session, [intake_record_id])
    return state


def get_lifecycle_state(
    session: Session, intake_record_id: int, settings: Settings
) -> IntakeLifecycleStateView:
    state = get_or_create_lifecycle_state(session, intake_record_id, settings)
    session.commit()
    session.refresh(state)
    view = _state_view(state)
    validate_lifecycle_response_safe(view)
    return view


def list_lifecycle_history(
    session: Session,
    intake_record_id: int,
    page: int,
    page_size: int,
    settings: Settings,
) -> IntakeLifecycleHistoryPage:
    _ensure_enabled(settings)
    if session.get(IntakeRecord, intake_record_id) is None:
        raise IntakeLifecycleError("Local intake record not found.")
    bounded_page = max(page, 1)
    bounded_size = min(
        max(page_size, 1), settings.intake_lifecycle_max_events_per_record
    )
    total = session.scalar(
        select(func.count())
        .select_from(IntakeReviewLifecycleEvent)
        .where(IntakeReviewLifecycleEvent.intake_record_id == intake_record_id)
    ) or 0
    rows = session.scalars(
        select(IntakeReviewLifecycleEvent)
        .where(IntakeReviewLifecycleEvent.intake_record_id == intake_record_id)
        .order_by(
            IntakeReviewLifecycleEvent.created_at.desc(),
            IntakeReviewLifecycleEvent.id.desc(),
        )
        .offset((bounded_page - 1) * bounded_size)
        .limit(bounded_size)
    )
    result = IntakeLifecycleHistoryPage(
        items=[_event_item(row) for row in rows],
        page=bounded_page,
        page_size=bounded_size,
        total_items=total,
        total_pages=math.ceil(total / bounded_size) if total else 0,
    )
    validate_lifecycle_response_safe(result)
    return result


def validate_lifecycle_transition(
    from_status: str | IntakeLifecycleStatus,
    to_status: str | IntakeLifecycleStatus,
    reason_code: str | IntakeLifecycleReasonCode | None,
    settings: Settings,
) -> None:
    _ensure_enabled(settings)
    try:
        source = IntakeLifecycleStatus(from_status)
        target = IntakeLifecycleStatus(to_status)
        reason = IntakeLifecycleReasonCode(reason_code) if reason_code else None
    except ValueError as exc:
        raise IntakeLifecycleBlockedError("Unsupported local lifecycle value.") from exc
    if FORBIDDEN.search(str(to_status)) or (
        reason_code and FORBIDDEN.search(str(reason_code))
    ):
        raise IntakeLifecycleBlockedError("Forbidden workflow language was blocked.")
    if settings.intake_lifecycle_require_reason and reason is None:
        raise IntakeLifecycleError("A bounded lifecycle reason code is required.")
    if target not in ALLOWED_TRANSITIONS[source]:
        raise IntakeLifecycleError("That local lifecycle transition is not allowed.")


def apply_lifecycle_transition(
    session: Session,
    intake_record_id: int,
    request: IntakeLifecycleTransitionRequest,
    settings: Settings,
) -> IntakeLifecycleTransitionResult:
    try:
        state = get_or_create_lifecycle_state(session, intake_record_id, settings)
        if state.event_count >= settings.intake_lifecycle_max_events_per_record:
            raise IntakeLifecycleBlockedError(
                "The bounded lifecycle event limit was reached."
            )
        validate_lifecycle_transition(
            state.status, request.to_status, request.reason_code, settings
        )
        if request.reason_summary and not settings.intake_lifecycle_allow_free_text_notes:
            raise IntakeLifecycleBlockedError("Free-text lifecycle notes are disabled.")
        summary = sanitize_lifecycle_value(
            request.reason_summary or REASON_SUMMARIES[request.reason_code]
        )
        if (
            not summary
            or len(summary) > settings.intake_lifecycle_max_reason_length
            or FORBIDDEN.search(summary)
        ):
            raise IntakeLifecycleBlockedError("Unsafe lifecycle reason was blocked.")
        actor_hash = (
            hash_lifecycle_actor(request.actor_label)
            if settings.intake_lifecycle_hash_actor
            else None
        )
        actor_masked = (
            mask_lifecycle_actor(request.actor_label)
            if settings.intake_lifecycle_mask_actor
            else None
        )
        event = IntakeReviewLifecycleEvent(
            intake_record_id=intake_record_id,
            from_status=state.status,
            to_status=request.to_status.value,
            reason_code=request.reason_code.value,
            reason_summary_sanitized=summary,
            actor_hash=actor_hash,
            actor_label_masked=actor_masked,
            request_id_hash=hash_lifecycle_actor(request.request_id),
        )
        session.add(event)
        state.status = request.to_status.value
        state.current_reason_code = request.reason_code.value
        state.current_reason_summary_sanitized = summary
        state.actor_hash = actor_hash
        state.actor_label_masked = actor_masked
        state.event_count += 1
        session.flush()
        result = IntakeLifecycleTransitionResult(
            state=_state_view(state), event=_event_item(event)
        )
        validate_lifecycle_response_safe(result)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def build_lifecycle_summary(
    session: Session, settings: Settings
) -> IntakeLifecycleSummary:
    if not settings.intake_lifecycle_enabled:
        return IntakeLifecycleSummary(
            enabled=False, message="Local intake lifecycle is disabled."
        )
    if not _safe_configuration(settings):
        return IntakeLifecycleSummary(
            enabled=False, message="Unsafe lifecycle exposure settings were blocked."
        )
    if not _tables_available(session):
        return IntakeLifecycleSummary(
            enabled=True, message="Lifecycle tables are not initialized; no local state read."
        )
    counts: dict[IntakeLifecycleStatus, int] = {}
    normalized_status_count = 0
    unknown_status_count = 0
    for raw_status, count in session.execute(
        select(IntakeReviewState.status, func.count()).group_by(
            IntakeReviewState.status
        )
    ):
        status, normalization = normalize_lifecycle_status(raw_status)
        counts[status] = counts.get(status, 0) + count
        if normalization is not None:
            normalized_status_count += count
            if normalization == "unknown_status_needs_review":
                unknown_status_count += count
    findings = []
    if normalized_status_count:
        findings.append(
            {
                "code": "legacy_status_normalized",
                "message": (
                    "Legacy local lifecycle labels were normalized to current canonical "
                    "labels for safe reporting."
                ),
                "severity": "warning",
            }
        )
    if unknown_status_count:
        findings.append(
            {
                "code": "unknown_status_needs_review",
                "message": (
                    "An unsupported local lifecycle value was represented as needs_follow_up "
                    "for safe reporting; review the source row before migration."
                ),
                "severity": "warning",
            }
        )
    summary = IntakeLifecycleSummary(
        enabled=True,
        total_states=sum(counts.values()),
        counts_by_status=counts,
        total_events=session.scalar(
            select(func.count()).select_from(IntakeReviewLifecycleEvent)
        )
        or 0,
        normalized_status_count=normalized_status_count,
        unknown_status_count=unknown_status_count,
        message="Sanitized local lifecycle state is available.",
        findings=findings,
    )
    validate_lifecycle_response_safe(summary)
    return summary


def validate_lifecycle_response_safe(response: BaseModel | dict[str, Any]) -> None:
    payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
    text = json.dumps(payload, default=str)
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
    keys = {str(key).casefold() for key in _walk_keys(payload)}
    if (
        keys & forbidden_keys
        or URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
    ):
        raise IntakeLifecycleBlockedError("Unsafe lifecycle response was blocked.")


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)
