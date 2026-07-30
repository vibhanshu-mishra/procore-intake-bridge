from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IntakeReviewTool(StrEnum):
    RFI = "rfi"
    SUBMITTAL = "submittal"
    UNKNOWN = "unknown"


class IntakeReviewWorkspaceStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    ERROR = "error"


class IntakeReviewSort(StrEnum):
    RECEIVED_AT_DESC = "received_at_desc"
    RECEIVED_AT_ASC = "received_at_asc"
    UPDATED_AT_DESC = "updated_at_desc"
    UPDATED_AT_ASC = "updated_at_asc"
    TOOL_ASC = "tool_asc"
    TOOL_DESC = "tool_desc"


class IntakeReviewFilter(BaseModel):
    tool: IntakeReviewTool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1)
    sort: IntakeReviewSort = IntakeReviewSort.RECEIVED_AT_DESC


class IntakeReviewFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class IntakeReviewPrioritySignal(BaseModel):
    code: str
    label: str


class IntakeReviewAttachmentSummary(BaseModel):
    manifest_count: int = 0
    declared_count: int = 0
    checksum_count: int = 0
    source_url_hash_count: int = 0
    content_types: dict[str, int] = Field(default_factory=dict)
    contents_read: bool = False
    paths_exposed: bool = False


class IntakeReviewSourceContext(BaseModel):
    project_id_masked: str | None = None
    project_id_hash: str | None = None
    item_id_masked: str | None = None
    item_id_hash: str | None = None
    sync_run_reference: str | None = None
    sync_mode: str | None = None
    sync_status: str | None = None
    matching_event_count: int = 0
    raw_ids_exposed: bool = False


class IntakeReviewRecordListItem(BaseModel):
    record_id: int
    tool: IntakeReviewTool
    display_number: str
    title: str
    source_status: str
    due_date: date | None = None
    received_at: datetime | None = None
    updated_at: datetime
    attachment_summary: IntakeReviewAttachmentSummary | None = None
    source_context: IntakeReviewSourceContext | None = None
    priority_signals: list[IntakeReviewPrioritySignal] = Field(default_factory=list)


class IntakeReviewRecordDetail(IntakeReviewRecordListItem):
    findings: list[IntakeReviewFinding] = Field(default_factory=list)
    read_only: bool = True
    lifecycle_transitions_available: bool = False
    raw_payload_exposed: bool = False


class IntakeReviewWorkspaceSummary(BaseModel):
    status: IntakeReviewWorkspaceStatus
    total_records: int = 0
    rfi_records: int = 0
    submittal_records: int = 0
    unknown_records: int = 0
    records_with_manifests: int = 0
    message: str
    read_only: bool = True
    procore_calls_made: bool = False
    external_calls_made: bool = False
    lifecycle_transitions_available: bool = False


class IntakeReviewWorkspacePage(BaseModel):
    status: IntakeReviewWorkspaceStatus
    items: list[IntakeReviewRecordListItem] = Field(default_factory=list)
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sort: IntakeReviewSort
    tool_filter: IntakeReviewTool | None = None
    read_only: bool = True


class IntakeReviewWorkspaceReport(BaseModel):
    summary: IntakeReviewWorkspaceSummary
    page: IntakeReviewWorkspacePage | None = None
    findings: list[IntakeReviewFinding] = Field(default_factory=list)

