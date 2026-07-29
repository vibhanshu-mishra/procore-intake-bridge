from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

VerificationStatus = Literal["unverified", "verified", "needs_review"]
StepStatus = Literal["passed", "failed", "blocked", "needs_review", "skipped"]


class WebhookDocsFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str


class WebhookDocsVerificationRecord(BaseModel):
    docs_checked_at: datetime | None = None
    docs_source_label: str = "Operator-supplied current Procore webhook documentation"
    docs_source_url_label: str = "current official Procore webhook documentation"
    observed_api_version: str = ""
    observed_scope_model: str = ""
    observed_deprecated_versions: list[str] = Field(default_factory=list)
    supported_event_assumptions: list[str] = Field(default_factory=list)
    signature_assumption_status: VerificationStatus = "unverified"
    payload_shape_assumption_status: VerificationStatus = "unverified"
    verification_notes: list[str] = Field(default_factory=list)
    verified_by_operator: str = ""
    status: VerificationStatus = "unverified"


class WebhookVerificationStepResult(BaseModel):
    name: str
    status: StepStatus
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class WebhookVerificationReport(BaseModel):
    generated_at: datetime
    environment: str
    synthetic_only: bool = True
    procore_calls: bool = False
    webhook_mutations: bool = False
    external_exposure: bool = False
    fixture_count: int
    docs_status: VerificationStatus
    steps: list[WebhookVerificationStepResult]
    overall_status: StepStatus


class WebhookVerificationPlan(BaseModel):
    enabled: bool
    environment: str
    confirmation_required: bool
    production_allowed: bool
    docs_check_required: bool
    configured_docs_status: str
    expected_payload_version: str
    expected_scope: str
    max_events: int
    write_report: bool
    synthetic_only: bool = True
    network_calls: bool = False
    procore_calls: bool = False
    webhook_mutations: bool = False
    steps: list[str]
    warning: str


class WebhookVerificationRequest(BaseModel):
    confirmation_phrase: str
    docs_record_path: str | None = None


class WebhookFixtureValidationResult(BaseModel):
    fixture_label: str
    status: StepStatus
    resource_type: str
    action: str
    event_fingerprint: str
    sensitive_fields_redacted: bool
    findings: list[str] = Field(default_factory=list)


class WebhookReceiverProbeResult(BaseModel):
    status: StepStatus
    accepted_count: int
    skipped_count: int
    duplicate_count: int = 0
    summary: str
