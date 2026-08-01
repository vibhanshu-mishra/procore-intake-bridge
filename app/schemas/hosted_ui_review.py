from enum import StrEnum

from pydantic import BaseModel, Field


class HostedUiReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_PRIVATE_REVIEW = "needs_private_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class HostedUiDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "hosted_ui_ready_for_maintainer_review"
    NEEDS_PRIVATE_REVIEW = "hosted_ui_needs_private_review"
    BLOCKED = "hosted_ui_blocked"
    NOT_RUN = "hosted_ui_not_run"


class HostedUiSurface(StrEnum):
    PRODUCT_DASHBOARD = "product_dashboard"
    ADMIN_DASHBOARD = "admin_dashboard"
    REVIEW_WORKSPACE = "review_workspace"
    TRIAGE_QUEUE = "triage_queue"
    LIFECYCLE_CONTROLS = "lifecycle_controls"
    ATTACHMENT_METADATA = "attachment_metadata"
    EXPORT_GUIDANCE = "export_guidance"
    SETUP_GUIDANCE = "setup_guidance"
    DEMO_WALKTHROUGH = "demo_walkthrough"
    API_REFERENCE = "api_reference"
    DEPLOYMENT_READINESS = "deployment_readiness"
    SECURITY_READINESS = "security_readiness"
    UNKNOWN = "unknown"


class HostedUiPageClass(StrEnum):
    LOCAL_DEMO_SAFE = "local_demo_safe"
    ADMIN_PROTECTED = "admin_protected"
    PRIVATE_REVIEW_REQUIRED = "private_review_required"
    METADATA_ONLY = "metadata_only"
    COMMAND_GUIDANCE_ONLY = "command_guidance_only"
    NOT_HOSTED_READY = "not_hosted_ready"
    UNKNOWN = "unknown"


class HostedUiProtectionType(StrEnum):
    INTENTIONALLY_PUBLIC = "intentionally_public"
    ADMIN_TOKEN_REQUIRED = "admin_token_required"
    LOCAL_ONLY = "local_only"
    METADATA_ONLY = "metadata_only"
    COMMAND_ONLY = "command_only"
    PRIVATE_WORKSPACE_REQUIRED = "private_workspace_required"
    DISABLED_BY_DEFAULT = "disabled_by_default"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    UNKNOWN = "unknown"


class HostedUiModeReadiness(StrEnum):
    DEMO_READY = "demo_ready"
    HOSTED_CANDIDATE = "hosted_candidate"
    HOSTED_NEEDS_PRIVATE_REVIEW = "hosted_needs_private_review"
    NOT_FOR_HOSTED_USE = "not_for_hosted_use"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class HostedUiFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    surface: HostedUiSurface | None = None
    location: str | None = None


class HostedUiPageItem(BaseModel):
    name: str
    source: str
    surface: HostedUiSurface
    page_class: HostedUiPageClass
    protection_type: HostedUiProtectionType
    mode_readiness: HostedUiModeReadiness
    purpose: str
    demo_safe: bool = False
    uses_local_demo_sqlite: bool = False
    admin_protected: bool = False
    metadata_only: bool = False
    command_guidance_only: bool = False
    external_frontend_assets: bool = False


class HostedUiRouteItem(BaseModel):
    path: str
    method: str
    surface: HostedUiSurface
    page_class: HostedUiPageClass
    protection_type: HostedUiProtectionType
    mode_readiness: HostedUiModeReadiness
    purpose: str
    admin_protected: bool = False
    local_only: bool = False
    metadata_only: bool = False
    export_download: bool = False
    file_serving: bool = False
    procore_write_back: bool = False


class HostedUiPrivateGate(BaseModel):
    code: str
    title: str
    description: str
    required_for_hosted_evaluation: bool = True
    public_repo_resolved: bool = False
    protection_type: HostedUiProtectionType = HostedUiProtectionType.PRIVATE_WORKSPACE_REQUIRED


class HostedUiReadinessChecklistItem(BaseModel):
    code: str
    description: str
    passed: bool
    private_review_required: bool = False
    evidence: str


class HostedUiReviewReport(BaseModel):
    status: HostedUiReviewStatus
    decision: HostedUiDecision
    pages: list[HostedUiPageItem] = Field(default_factory=list)
    routes: list[HostedUiRouteItem] = Field(default_factory=list)
    private_gates: list[HostedUiPrivateGate] = Field(default_factory=list)
    checklist: list[HostedUiReadinessChecklistItem] = Field(default_factory=list)
    pages_total: int
    routes_total: int
    demo_ready_pages_total: int
    hosted_candidate_pages_total: int
    private_review_pages_total: int
    blocked_pages_total: int
    findings: list[HostedUiFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    route_inventory_complete: bool
    page_inventory_complete: bool
    admin_surfaces_protected: bool
    attachment_surfaces_metadata_only: bool
    export_download_routes_present: bool = False
    file_serving_routes_present: bool = False
    external_frontend_assets_present: bool = False
    frontend_build_system_added: bool = False
    hosted_deployment_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    production_approval_claimed: bool = False
    release_approval_claimed: bool = False
    pilot_approval_claimed: bool = False
    deployment_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class HostedUiArtifactResult(BaseModel):
    status: HostedUiReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    hosted_deployment: bool = False
    frontend_build: bool = False
