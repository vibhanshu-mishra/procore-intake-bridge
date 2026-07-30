from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SandboxReadValidationStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    PASSED = "passed"
    FAILED = "failed"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    EMPTY_RESULT = "empty_result"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class SandboxReadValidationDecision(StrEnum):
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_NEEDS_REVIEW = "validation_needs_review"
    VALIDATION_BLOCKED = "validation_blocked"
    VALIDATION_NOT_RUN = "validation_not_run"


class SandboxReadValidationTool(StrEnum):
    RFIS = "rfis"
    SUBMITTALS = "submittals"


class SandboxReadValidationFinding(BaseModel):
    code: str
    status: SandboxReadValidationStatus
    message: str
    blocking: bool = False


class SandboxReadValidationRequirement(BaseModel):
    name: str
    status: SandboxReadValidationStatus
    guidance: str


class SandboxReadValidationScope(BaseModel):
    company_scope_configured: bool = False
    project_scope_configured: bool = False
    configured_project_count: int = 0
    project_scope_hashes: tuple[str, ...] = ()
    raw_identifiers_included: bool = False


class SandboxReadValidationProbe(BaseModel):
    name: str
    status: SandboxReadValidationStatus
    item_count: int = 0
    pages_attempted: int = 0
    detail_attempted: bool = False
    filtering_represented: bool = False
    summary: str


class SandboxReadValidationToolResult(BaseModel):
    tool: SandboxReadValidationTool
    status: SandboxReadValidationStatus
    list_status: SandboxReadValidationStatus
    detail_status: SandboxReadValidationStatus
    sanitized_item_count: int = 0
    identifier_hashes: tuple[str, ...] = ()
    pages_attempted: int = 0
    filtering_represented: bool = True
    probes: tuple[SandboxReadValidationProbe, ...] = ()


class SandboxReadValidationEvidenceRef(BaseModel):
    validation_ref: str
    run_label: str
    scope_ref: str
    rfi_access_status: str
    submittal_access_status: str
    pagination_status: str
    date_filter_status: str
    reviewer_placeholder: str
    expiry_placeholder: str
    report_contents_included: bool = False
    private_only: bool = True


class SandboxReadValidationOutputPolicy(BaseModel):
    attachments_included: bool = False
    attachment_downloads_attempted: bool = False
    raw_payloads_stored: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    private_paths_exposed: bool = False
    external_calls_from_planning: bool = False


class SandboxReadValidationReport(BaseModel):
    status: SandboxReadValidationStatus
    decision: SandboxReadValidationDecision
    validation_attempted: bool = False
    live_calls_attempted: bool = False
    provider_mode: str
    selected_tools: tuple[SandboxReadValidationTool, ...]
    max_projects: int
    max_items_per_tool: int
    max_pages: int
    timeout_seconds: int
    scope: SandboxReadValidationScope
    requirements: tuple[SandboxReadValidationRequirement, ...] = ()
    findings: tuple[SandboxReadValidationFinding, ...] = ()
    tool_summaries: tuple[SandboxReadValidationToolResult, ...] = ()
    output_policy: SandboxReadValidationOutputPolicy = Field(
        default_factory=SandboxReadValidationOutputPolicy
    )
    evidence_ref: SandboxReadValidationEvidenceRef
    recommended_next_steps: tuple[str, ...] = ()
    generated_at: datetime


class SandboxReadValidationArtifactResult(BaseModel):
    output_directory: str
    files: tuple[str, ...]
    live_calls_attempted: bool
    raw_payloads_stored: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    private_paths_exposed: bool = False
