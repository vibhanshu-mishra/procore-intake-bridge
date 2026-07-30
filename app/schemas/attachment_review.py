from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.intake_review_workspace import IntakeReviewTool


class AttachmentReviewStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    ERROR = "error"


class AttachmentReviewSort(StrEnum):
    RECORD_RECEIVED_AT_DESC = "record_received_at_desc"
    RECORD_RECEIVED_AT_ASC = "record_received_at_asc"
    ATTACHMENT_COUNT_DESC = "attachment_count_desc"
    ATTACHMENT_COUNT_ASC = "attachment_count_asc"
    TOOL_ASC = "tool_asc"
    TOOL_DESC = "tool_desc"
    STORAGE_STATUS_ASC = "storage_status_asc"
    STORAGE_STATUS_DESC = "storage_status_desc"


class AttachmentReviewAvailability(StrEnum):
    MANIFEST_PRESENT = "manifest_present"
    MANIFEST_MISSING = "manifest_missing"
    ATTACHMENT_PLANNED = "attachment_planned"
    ATTACHMENT_STORED_METADATA_ONLY = "attachment_stored_metadata_only"
    ATTACHMENT_SKIPPED = "attachment_skipped"
    ATTACHMENT_BLOCKED = "attachment_blocked"
    ATTACHMENT_UNAVAILABLE_BY_DESIGN = "attachment_unavailable_by_design"
    UNKNOWN = "unknown"


class AttachmentReviewStorageStatus(StrEnum):
    NOT_DOWNLOADED = "not_downloaded"
    FIXTURE_METADATA_AVAILABLE = "fixture_metadata_available"
    LOCAL_METADATA_AVAILABLE = "local_metadata_available"
    CLOUD_METADATA_AVAILABLE = "cloud_metadata_available"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class AttachmentReviewChecksumStatus(StrEnum):
    CHECKSUM_PRESENT = "checksum_present"
    CHECKSUM_MISSING = "checksum_missing"
    CHECKSUM_NOT_APPLICABLE = "checksum_not_applicable"
    UNKNOWN = "unknown"


class AttachmentReviewFileCategory(StrEnum):
    PDF_LIKE = "pdf_like"
    IMAGE_LIKE = "image_like"
    DRAWING_LIKE = "drawing_like"
    SPREADSHEET_LIKE = "spreadsheet_like"
    TEXT_LIKE = "text_like"
    ARCHIVE_LIKE = "archive_like"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class AttachmentReviewFilter(BaseModel):
    availability: AttachmentReviewAvailability | None = None
    tool: IntakeReviewTool | None = None
    storage_status: AttachmentReviewStorageStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1)
    sort: AttachmentReviewSort = AttachmentReviewSort.RECORD_RECEIVED_AT_DESC


class AttachmentReviewFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class AttachmentReviewManifestSummary(BaseModel):
    availability: AttachmentReviewAvailability
    manifest_count: int = 0
    planned_count: int = 0
    stored_metadata_count: int = 0
    skipped_count: int = 0
    blocked_count: int = 0
    size_known_count: int = 0
    total_size_bytes: int = 0
    checksum_present_count: int = 0
    checksum_missing_count: int = 0
    source_available_count: int = 0
    file_categories: dict[AttachmentReviewFileCategory, int] = Field(default_factory=dict)
    storage_statuses: dict[AttachmentReviewStorageStatus, int] = Field(default_factory=dict)
    contents_available: bool = False
    contents_read: bool = False
    paths_exposed: bool = False
    keys_exposed: bool = False
    urls_exposed: bool = False
    filenames_exposed: bool = False


class AttachmentReviewItem(BaseModel):
    attachment_id_masked: str | None = None
    attachment_id_hash: str | None = None
    availability: AttachmentReviewAvailability
    storage_status: AttachmentReviewStorageStatus
    checksum_status: AttachmentReviewChecksumStatus
    file_category: AttachmentReviewFileCategory
    size_bytes: int | None = None
    source_available: bool = False
    contents_available: bool = False


class AttachmentReviewRecordSummary(BaseModel):
    record_id: int
    tool: IntakeReviewTool
    display_number: str
    title: str
    received_at: datetime | None = None
    manifest: AttachmentReviewManifestSummary
    read_only: bool = True


class AttachmentReviewRecordDetail(AttachmentReviewRecordSummary):
    items: list[AttachmentReviewItem] = Field(default_factory=list)
    findings: list[AttachmentReviewFinding] = Field(default_factory=list)


class AttachmentReviewPage(BaseModel):
    status: AttachmentReviewStatus
    items: list[AttachmentReviewRecordSummary] = Field(default_factory=list)
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sort: AttachmentReviewSort
    availability_filter: AttachmentReviewAvailability | None = None
    tool_filter: IntakeReviewTool | None = None
    storage_status_filter: AttachmentReviewStorageStatus | None = None
    read_only: bool = True


class AttachmentReviewWorkspaceSummary(BaseModel):
    status: AttachmentReviewStatus
    total_records: int = 0
    records_with_manifests: int = 0
    records_without_manifests: int = 0
    planned_attachments: int = 0
    stored_metadata_attachments: int = 0
    skipped_attachments: int = 0
    blocked_attachments: int = 0
    message: str
    metadata_only: bool = True
    contents_available: bool = False
    read_only: bool = True
    procore_calls_made: bool = False
    external_calls_made: bool = False
    storage_calls_made: bool = False
