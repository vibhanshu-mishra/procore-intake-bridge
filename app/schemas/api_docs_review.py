from enum import StrEnum

from pydantic import BaseModel, Field


class ApiDocsReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class ApiDocsDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "api_docs_ready_for_maintainer_review"
    NEEDS_REVIEW = "api_docs_needs_review"
    BLOCKED = "api_docs_blocked"
    NOT_RUN = "api_docs_not_run"


class ApiRouteClass(StrEnum):
    PUBLIC_HEALTH = "public_health"
    PUBLIC_READINESS = "public_readiness"
    ADMIN_DASHBOARD = "admin_dashboard"
    DEPLOYMENT_READINESS = "deployment_readiness"
    PRODUCT_DASHBOARD = "product_dashboard"
    REVIEW_WORKSPACE = "review_workspace"
    REVIEW_API = "review_api"
    LIFECYCLE_LOCAL_MUTATION = "lifecycle_local_mutation"
    WEBHOOK_SIGNATURE_BOUNDARY = "webhook_signature_boundary"
    INTAKE_SYNC_DEMO = "intake_sync_demo"
    ATTACHMENT_METADATA = "attachment_metadata"
    ONBOARDING_PACKET = "onboarding_packet"
    SANDBOX_GATED = "sandbox_gated"
    DIAGNOSTICS_SUPPORT = "diagnostics_support"
    STATIC_OR_DOCS = "static_or_docs"
    UNKNOWN = "unknown"


class ApiProtectionType(StrEnum):
    INTENTIONALLY_PUBLIC = "intentionally_public"
    ADMIN_TOKEN_REQUIRED = "admin_token_required"
    WEBHOOK_SIGNATURE_REQUIRED = "webhook_signature_required"
    LOCAL_ONLY = "local_only"
    DEMO_ONLY = "demo_only"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    PRIVATE_WORKSPACE_REQUIRED = "private_workspace_required"
    DISABLED_BY_DEFAULT = "disabled_by_default"
    METADATA_ONLY = "metadata_only"
    UNKNOWN = "unknown"


class ApiMethodRisk(StrEnum):
    SAFE_GET = "safe_get"
    LOCAL_ONLY_POST = "local_only_post"
    WEBHOOK_POST_SIGNATURE_REQUIRED = "webhook_post_signature_required"
    DESTRUCTIVE_OR_LIVE_MUTATION = "destructive_or_live_mutation"
    UNKNOWN = "unknown"


class ApiRouteDocumentationItem(BaseModel):
    path: str
    method: str
    name: str
    purpose: str
    route_class: ApiRouteClass
    protection_type: ApiProtectionType
    method_risk: ApiMethodRisk
    intentionally_public: bool = False
    admin_guard_present: bool = False
    local_only: bool = False
    serves_files: bool = False
    export_download: bool = False
    procore_write_back: bool = False
    notes: str = ""


class ApiUsageExample(BaseModel):
    title: str
    method: str
    route: str
    example: str
    description: str
    local_only: bool = True
    fake_data_only: bool = True
    live_call: bool = False


class ApiDocsFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    route: str | None = None


class ApiDocsReport(BaseModel):
    status: ApiDocsReviewStatus
    decision: ApiDocsDecision
    routes: list[ApiRouteDocumentationItem] = Field(default_factory=list)
    usage_examples: list[ApiUsageExample] = Field(default_factory=list)
    routes_total: int
    documented_routes_total: int
    undocumented_routes_total: int
    public_routes_total: int
    protected_routes_total: int
    local_mutation_routes_total: int
    webhook_routes_total: int
    unsafe_routes_total: int
    findings: list[ApiDocsFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    all_routes_documented: bool
    no_export_download_routes: bool
    no_file_serving_routes: bool
    no_procore_write_routes: bool
    demo_examples_safe: bool
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    openapi_external_tool_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    production_approval_claimed: bool = False
    release_approval_claimed: bool = False
    pilot_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class ApiDocsArtifactResult(BaseModel):
    status: ApiDocsReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    external_operations: bool = False
