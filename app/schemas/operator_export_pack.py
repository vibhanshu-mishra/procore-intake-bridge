from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OperatorExportFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "md"
    CSV = "csv"


class OperatorExportSection(StrEnum):
    INTAKE_SUMMARY = "intake_summary"
    INTAKE_RECORDS = "intake_records"
    LIFECYCLE_SUMMARY = "lifecycle_summary"
    LIFECYCLE_EVENTS = "lifecycle_events"
    TRIAGE_SUMMARY = "triage_summary"
    ATTACHMENT_SUMMARY = "attachment_summary"
    COMBINED_PACKET = "combined_packet"


class OperatorExportStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    ERROR = "error"
    WRITTEN = "written"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class OperatorExportFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class OperatorExportFilter(BaseModel):
    sections: list[OperatorExportSection] = Field(default_factory=list)
    formats: list[OperatorExportFormat] = Field(default_factory=list)
    max_records: int = Field(default=1000, ge=1)


class OperatorExportMetadata(BaseModel):
    status: OperatorExportStatus
    generated_at: datetime
    local_record_limit: int
    raw_payloads_exposed: bool = False
    source_urls_exposed: bool = False
    signed_urls_exposed: bool = False
    storage_keys_exposed: bool = False
    private_paths_exposed: bool = False
    original_filenames_exposed: bool = False
    contents_exposed: bool = False
    secrets_exposed: bool = False
    raw_source_ids_exposed: bool = False
    compliance_or_approval_claimed: bool = False
    procore_calls_made: bool = False
    external_calls_made: bool = False
    database_writes_made: bool = False
    storage_calls_made: bool = False


class OperatorExportIntakeSummary(BaseModel):
    status: OperatorExportStatus
    total_records: int = 0
    exported_records: int = 0
    rfi_records: int = 0
    submittal_records: int = 0
    unknown_records: int = 0
    records_with_manifests: int = 0
    records: list[dict[str, object]] = Field(default_factory=list)


class OperatorExportLifecycleSummary(BaseModel):
    status: OperatorExportStatus
    total_states: int = 0
    total_events: int = 0
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    local_labels_only: bool = True


class OperatorExportTriageSummary(BaseModel):
    status: OperatorExportStatus
    total_records: int = 0
    bucket_counts: dict[str, int] = Field(default_factory=dict)
    lifecycle_distribution: dict[str, int] = Field(default_factory=dict)
    description: str = "Deterministic local sorting summary only."


class OperatorExportAttachmentSummary(BaseModel):
    status: OperatorExportStatus
    total_records: int = 0
    records_with_manifests: int = 0
    records_without_manifests: int = 0
    planned_attachments: int = 0
    stored_metadata_attachments: int = 0
    skipped_attachments: int = 0
    blocked_attachments: int = 0
    metadata_only: bool = True
    contents_available: bool = False


class OperatorExportEventSummary(BaseModel):
    status: OperatorExportStatus
    total_events: int = 0
    exported_events: int = 0
    counts_by_transition: dict[str, int] = Field(default_factory=dict)
    counts_by_reason: dict[str, int] = Field(default_factory=dict)
    events: list[dict[str, object]] = Field(default_factory=list)


class OperatorExportCombinedPacket(BaseModel):
    metadata: OperatorExportMetadata
    intake: OperatorExportIntakeSummary | None = None
    lifecycle: OperatorExportLifecycleSummary | None = None
    triage: OperatorExportTriageSummary | None = None
    attachments: OperatorExportAttachmentSummary | None = None
    events: OperatorExportEventSummary | None = None
    findings: list[OperatorExportFinding] = Field(default_factory=list)
    summary_disclaimer: str = (
        "Local sanitized metadata summary only; not an official external report."
    )


class OperatorExportArtifactResult(BaseModel):
    status: OperatorExportStatus
    output_directory: str
    files: list[str] = Field(default_factory=list)
    formats: list[OperatorExportFormat] = Field(default_factory=list)
    values_exposed: bool = False
    external_calls_made: bool = False
