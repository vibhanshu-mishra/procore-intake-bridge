from enum import StrEnum

from pydantic import BaseModel, Field


class AuthBoundaryAuditStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class AuthBoundaryDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "auth_boundary_ready_for_security_review"
    NEEDS_REVIEW = "auth_boundary_needs_review"
    BLOCKED = "auth_boundary_blocked"
    NOT_RUN = "auth_boundary_not_run"


class AuthBoundarySurfaceType(StrEnum):
    ROUTE = "route"
    COMMAND = "command"
    GENERATED_OUTPUT = "generated_output"
    PRIVATE_WORKSPACE = "private_workspace"


class AuthBoundaryRouteClass(StrEnum):
    PUBLIC_HEALTH = "public_health"
    PUBLIC_READINESS = "public_readiness"
    PROTECTED_ADMIN = "protected_admin"
    PROTECTED_DEPLOYMENT = "protected_deployment"
    PROTECTED_PRODUCT_DASHBOARD = "protected_product_dashboard"
    PROTECTED_REVIEW_WORKSPACE = "protected_review_workspace"
    PROTECTED_REVIEW_API = "protected_review_api"
    PROTECTED_LIFECYCLE_LOCAL_MUTATION = "protected_lifecycle_local_mutation"
    WEBHOOK_SIGNATURE_REQUIRED = "webhook_signature_required"
    DOCS_OR_STATIC_LOCAL = "docs_or_static_local"
    UNKNOWN = "unknown"


class AuthBoundaryProtectionType(StrEnum):
    INTENTIONALLY_PUBLIC = "intentionally_public"
    ADMIN_TOKEN_REQUIRED = "admin_token_required"
    WEBHOOK_SIGNATURE_REQUIRED = "webhook_signature_required"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"
    SECRET_PROVIDER_REQUIRED = "secret_provider_required"
    PRIVATE_WORKSPACE_REQUIRED = "private_workspace_required"
    DISABLED_BY_DEFAULT = "disabled_by_default"
    LOCAL_ONLY = "local_only"
    NO_NETWORK = "no_network"
    UNKNOWN = "unknown"


class AuthBoundaryMethodRisk(StrEnum):
    SAFE_GET = "safe_get"
    LOCAL_ONLY_POST = "local_only_post"
    WEBHOOK_POST_SIGNATURE_REQUIRED = "webhook_post_signature_required"
    UNSAFE_MUTATION = "unsafe_mutation"
    UNKNOWN = "unknown"


class AuthBoundaryFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class AuthBoundaryRouteItem(BaseModel):
    path: str
    method: str
    surface_type: AuthBoundarySurfaceType = AuthBoundarySurfaceType.ROUTE
    route_class: AuthBoundaryRouteClass
    protection_type: AuthBoundaryProtectionType
    method_risk: AuthBoundaryMethodRisk
    admin_guard_present: bool = False
    local_only: bool = False
    notes: str = ""


class AuthBoundaryCommandItem(BaseModel):
    name: str
    surface_type: AuthBoundarySurfaceType = AuthBoundarySurfaceType.COMMAND
    protection_type: AuthBoundaryProtectionType
    live_capable: bool = False
    included_in_quality: bool = False
    documented_gate: bool = True


class AuthBoundaryControl(BaseModel):
    name: str
    protection_type: AuthBoundaryProtectionType
    evidence_path: str
    description: str


class AuthBoundaryReport(BaseModel):
    status: AuthBoundaryAuditStatus
    decision: AuthBoundaryDecision
    routes: list[AuthBoundaryRouteItem]
    commands: list[AuthBoundaryCommandItem]
    controls: list[AuthBoundaryControl]
    routes_total: int
    commands_total: int
    protected_routes_total: int
    public_routes_total: int
    local_mutation_routes_total: int
    webhook_routes_total: int
    unknown_routes_total: int
    unsafe_routes_total: int
    findings: list[AuthBoundaryFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    public_routes_are_limited: bool
    admin_routes_protected: bool
    review_routes_protected: bool
    lifecycle_posts_local_only: bool
    webhook_signature_required: bool
    live_commands_gated: bool
    export_download_routes_present: bool = False
    file_serving_routes_present: bool = False
    procore_write_routes_present: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class AuthBoundaryArtifactResult(BaseModel):
    status: AuthBoundaryAuditStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
