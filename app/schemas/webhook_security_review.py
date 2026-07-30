from enum import StrEnum

from pydantic import BaseModel, Field


class WebhookSecurityReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class WebhookSecurityDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "webhook_security_ready_for_security_review"
    NEEDS_REVIEW = "webhook_security_needs_review"
    BLOCKED = "webhook_security_blocked"
    NOT_RUN = "webhook_security_not_run"


class WebhookSecurityCategory(StrEnum):
    SIGNATURE_VERIFICATION = "signature_verification"
    CONSTANT_TIME_COMPARISON = "constant_time_comparison"
    RAW_BODY_CANONICALIZATION = "raw_body_canonicalization"
    TIMESTAMP_OR_REPLAY_BOUNDARY = "timestamp_or_replay_boundary"
    EVENT_FINGERPRINTING = "event_fingerprinting"
    DEDUPLICATION = "deduplication"
    QUEUE_STORAGE = "queue_storage"
    RETRY_REPLAY_TOOLING = "retry_replay_tooling"
    REDACTION_AND_LOGGING = "redaction_and_logging"
    FIXTURE_SAFETY = "fixture_safety"
    LIVE_REGISTRATION_BOUNDARY = "live_registration_boundary"
    OPERATOR_RUNBOOK_BOUNDARY = "operator_runbook_boundary"


class WebhookSecurityBoundary(BaseModel):
    name: str
    description: str
    private_review_required: bool = False


class WebhookSecurityFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class WebhookSecurityControl(BaseModel):
    name: str
    category: WebhookSecurityCategory
    evidence_path: str
    implemented: bool = True
    description: str


class WebhookSecurityScenario(BaseModel):
    category: WebhookSecurityCategory
    boundary: str
    expectation: str


class WebhookSignatureExpectation(BaseModel):
    raw_body_used: bool
    constant_time_compare: bool
    shared_secret_value_exposed: bool = False
    signature_value_exposed: bool = False


class WebhookReplayExpectation(BaseModel):
    local_only: bool
    live_endpoint_called: bool = False
    timestamp_window_implemented: bool = False
    deduplication_implemented: bool = True


class WebhookFixtureMatrixItem(BaseModel):
    fixture_name: str
    placeholder_only: bool = True
    live_payload: bool = False
    live_headers: bool = False
    signature_included: bool = False


class WebhookSecurityReviewReport(BaseModel):
    status: WebhookSecurityReviewStatus
    decision: WebhookSecurityDecision
    categories: list[WebhookSecurityCategory]
    boundaries: list[WebhookSecurityBoundary]
    controls: list[WebhookSecurityControl]
    scenarios: list[WebhookSecurityScenario]
    signature_expectation: WebhookSignatureExpectation
    replay_expectation: WebhookReplayExpectation
    fixture_matrix: list[WebhookFixtureMatrixItem]
    categories_total: int
    controls_total: int
    scenarios_total: int
    findings: list[WebhookSecurityFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    webhook_routes_total: int
    webhook_post_routes_total: int
    signature_verification_documented: bool
    constant_time_compare_documented: bool
    replay_boundary_documented: bool
    deduplication_documented: bool
    redacted_failures_documented: bool
    live_replay_attempted: bool = False
    webhook_registration_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    webhook_secrets_exposed: bool = False
    live_headers_exposed: bool = False
    live_payloads_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class WebhookSecurityArtifactResult(BaseModel):
    status: WebhookSecurityReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
