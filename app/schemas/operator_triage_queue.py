from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.intake_lifecycle import IntakeLifecycleStatus
from app.schemas.intake_review_workspace import IntakeReviewTool


class OperatorTriageStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    ERROR = "error"


class OperatorTriageSort(StrEnum):
    PRIORITY_DESC = "priority_desc"
    PRIORITY_ASC = "priority_asc"
    RECEIVED_AT_DESC = "received_at_desc"
    RECEIVED_AT_ASC = "received_at_asc"
    LIFECYCLE_STATUS_ASC = "lifecycle_status_asc"
    LIFECYCLE_STATUS_DESC = "lifecycle_status_desc"
    TOOL_ASC = "tool_asc"
    TOOL_DESC = "tool_desc"


class OperatorTriageBucket(StrEnum):
    NEEDS_FOLLOW_UP = "needs_follow_up"
    NEW_UNREVIEWED = "new_unreviewed"
    IN_REVIEW = "in_review"
    OLDER_UNREVIEWED = "older_unreviewed"
    RECENTLY_RECEIVED = "recently_received"
    HAS_ATTACHMENTS = "has_attachments"
    MISSING_SOURCE_CONTEXT = "missing_source_context"
    UNKNOWN_TOOL = "unknown_tool"
    REVIEWED = "reviewed"
    IGNORED = "ignored"


class OperatorTriageSignal(BaseModel):
    code: str
    label: str
    weight: int


class OperatorTriageFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class OperatorTriageFilter(BaseModel):
    bucket: OperatorTriageBucket | None = None
    tool: IntakeReviewTool | None = None
    lifecycle_status: IntakeLifecycleStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1)
    sort: OperatorTriageSort = OperatorTriageSort.PRIORITY_DESC


class OperatorTriageQueueItem(BaseModel):
    record_id: int
    tool: IntakeReviewTool
    display_number: str
    title: str
    lifecycle_status: IntakeLifecycleStatus
    received_at: datetime | None = None
    updated_at: datetime
    source_id_masked: str | None = None
    source_id_hash: str | None = None
    attachment_manifest_count: int = 0
    signals: list[OperatorTriageSignal] = Field(default_factory=list)
    buckets: list[OperatorTriageBucket] = Field(default_factory=list)
    priority_score: int = 0
    priority_description: str = "Local sorting helper only."
    read_only: bool = True


class OperatorTriageQueuePage(BaseModel):
    status: OperatorTriageStatus
    items: list[OperatorTriageQueueItem] = Field(default_factory=list)
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sort: OperatorTriageSort
    bucket_filter: OperatorTriageBucket | None = None
    tool_filter: IntakeReviewTool | None = None
    lifecycle_filter: IntakeLifecycleStatus | None = None
    read_only: bool = True


class OperatorTriageBucketSummary(BaseModel):
    bucket: OperatorTriageBucket
    count: int


class OperatorTriageQueueSummary(BaseModel):
    status: OperatorTriageStatus
    total_records: int = 0
    buckets: list[OperatorTriageBucketSummary] = Field(default_factory=list)
    lifecycle_distribution: dict[IntakeLifecycleStatus, int] = Field(default_factory=dict)
    message: str
    priority_description: str = "Priority is a deterministic local sorting helper only."
    read_only: bool = True
    procore_calls_made: bool = False
    external_calls_made: bool = False


class OperatorTriageDashboardView(BaseModel):
    summary: OperatorTriageQueueSummary
    queue: OperatorTriageQueuePage
    findings: list[OperatorTriageFinding] = Field(default_factory=list)
