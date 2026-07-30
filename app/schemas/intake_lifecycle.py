from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IntakeLifecycleStatus(StrEnum):
    NEW = "new"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    IGNORED = "ignored"


class IntakeLifecycleReasonCode(StrEnum):
    INITIAL_REVIEW_STARTED = "initial_review_started"
    REVIEWED_NO_ACTION_NEEDED = "reviewed_no_action_needed"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    DUPLICATE_OR_IRRELEVANT = "duplicate_or_irrelevant"
    REOPENED_FOR_REVIEW = "reopened_for_review"
    MARKED_IN_ERROR = "marked_in_error"
    DEMO_PLACEHOLDER_REASON = "demo_placeholder_reason"


class IntakeLifecycleTransition(BaseModel):
    from_status: IntakeLifecycleStatus
    to_status: IntakeLifecycleStatus
    reason_code: IntakeLifecycleReasonCode


class IntakeLifecycleTransitionRequest(BaseModel):
    to_status: IntakeLifecycleStatus
    reason_code: IntakeLifecycleReasonCode
    reason_summary: str | None = None
    actor_label: str = "LOCAL_OPERATOR_PLACEHOLDER"
    request_id: str | None = None


class IntakeLifecycleEventItem(BaseModel):
    event_id: int
    from_status: IntakeLifecycleStatus
    to_status: IntakeLifecycleStatus
    reason_code: IntakeLifecycleReasonCode
    reason_summary_sanitized: str
    actor_hash: str | None = None
    actor_label_masked: str | None = None
    request_id_hash: str | None = None
    source: str
    created_at: datetime


class IntakeLifecycleStateView(BaseModel):
    intake_record_id: int
    status: IntakeLifecycleStatus
    current_reason_code: IntakeLifecycleReasonCode | None = None
    current_reason_summary_sanitized: str | None = None
    actor_hash: str | None = None
    actor_label_masked: str | None = None
    event_count: int = 0
    created_at: datetime
    updated_at: datetime
    local_only: bool = True
    procore_updated: bool = False


class IntakeLifecycleTransitionResult(BaseModel):
    state: IntakeLifecycleStateView
    event: IntakeLifecycleEventItem
    local_only: bool = True
    external_calls_made: bool = False


class IntakeLifecycleHistoryPage(BaseModel):
    items: list[IntakeLifecycleEventItem] = Field(default_factory=list)
    page: int
    page_size: int
    total_items: int
    total_pages: int
    local_only: bool = True


class IntakeLifecycleFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class IntakeLifecycleSummary(BaseModel):
    enabled: bool
    total_states: int = 0
    counts_by_status: dict[IntakeLifecycleStatus, int] = Field(default_factory=dict)
    total_events: int = 0
    message: str
    local_only: bool = True
    procore_calls_made: bool = False
    external_calls_made: bool = False
    findings: list[IntakeLifecycleFinding] = Field(default_factory=list)
