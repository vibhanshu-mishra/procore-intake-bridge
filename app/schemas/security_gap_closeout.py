from enum import StrEnum

from pydantic import BaseModel, Field


class SecurityGapCloseoutStatus(StrEnum):
    READY = "ready"
    NEEDS_PRIVATE_REVIEW = "needs_private_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class SecurityGapCloseoutDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "security_gap_closeout_ready_for_maintainer_review"
    NEEDS_PRIVATE_REVIEW = "security_gap_closeout_needs_private_review"
    BLOCKED = "security_gap_closeout_blocked"
    NOT_RUN = "security_gap_closeout_not_run"


class SecurityGapDomain(StrEnum):
    PRIVACY_REVIEW_TEMPLATE = "privacy_review_template"
    ENCRYPTION_AT_REST_GUIDANCE = "encryption_at_rest_guidance"
    RETENTION_POLICY_VS_ENFORCEMENT = "retention_policy_vs_enforcement"
    AUDIT_LOGGING_POLICY_VS_IMPLEMENTATION = "audit_logging_policy_vs_implementation"
    NOTIFICATION_BOUNDARY = "notification_boundary"
    INCIDENT_RESPONSE_PRIVATE_GAPS = "incident_response_private_gaps"
    PROVIDER_PERMISSIONS_PRIVATE_REVIEW = "provider_permissions_private_review"
    DATABASE_ROLES_PRIVATE_REVIEW = "database_roles_private_review"
    CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW = "customer_data_handling_private_review"
    RELEASE_SECURITY_PRIVATE_REVIEW = "release_security_private_review"
    LEGAL_COMPLIANCE_PRIVATE_REVIEW = "legal_compliance_private_review"
    OPERATIONAL_MONITORING_FUTURE_WORK = "operational_monitoring_future_work"
    PUBLIC_PRIVATE_BOUNDARY = "public_private_boundary"
    PRODUCT_LIMITATIONS = "product_limitations"


class ImplementationLevel(StrEnum):
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    POLICY_ONLY = "policy_only"
    GUIDANCE_ONLY = "guidance_only"
    INTENTIONALLY_NOT_IMPLEMENTED = "intentionally_not_implemented"
    PRIVATE_REVIEW_REQUIRED = "private_review_required"
    FUTURE_WORK = "future_work"
    OUT_OF_SCOPE = "out_of_scope"


class SecurityGapFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: SecurityGapDomain | None = None


class SecurityGapControl(BaseModel):
    name: str
    domain: SecurityGapDomain
    description: str
    evidence_path: str | None = None
    present: bool = False


class SecurityGapItem(BaseModel):
    code: str
    domain: SecurityGapDomain
    title: str
    implementation_level: ImplementationLevel
    summary: str
    private_review_required: bool = False


class PolicyImplementationMatrixItem(BaseModel):
    capability: str
    domain: SecurityGapDomain
    implementation_level: ImplementationLevel
    public_repo_position: str
    private_review_required: bool = False


class PrivateSecurityActionItem(BaseModel):
    code: str
    domain: SecurityGapDomain
    action: str
    private_review_reference: str = "PRIVATE_REVIEW_REF_PLACEHOLDER"
    completed: bool = False


class PrivacyTemplateSection(BaseModel):
    code: str
    title: str
    guidance: str
    legal_review_reference: str = "LEGAL_REVIEW_REF_PLACEHOLDER"
    compliance_claimed: bool = False


class EncryptionGuidanceItem(BaseModel):
    code: str
    component: str
    guidance: str
    private_review_required: bool = True
    implemented_by_app: bool = False


class KnownLimitationItem(BaseModel):
    code: str
    domain: SecurityGapDomain
    limitation: str
    implementation_level: ImplementationLevel


class SecurityGapCloseoutReport(BaseModel):
    status: SecurityGapCloseoutStatus
    decision: SecurityGapCloseoutDecision
    domains_total: int
    implemented_items_total: int
    partial_items_total: int
    policy_only_items_total: int
    guidance_only_items_total: int
    intentionally_not_implemented_items_total: int
    private_review_items_total: int
    future_work_items_total: int
    findings: list[SecurityGapFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    private_review_required: bool = True
    privacy_compliance_claimed: bool = False
    legal_compliance_claimed: bool = False
    security_certification_claimed: bool = False
    production_approval_granted: bool = False
    pilot_approval_granted: bool = False
    release_approval_granted: bool = False
    deployment_approval_granted: bool = False
    encryption_at_rest_implemented_by_app: bool = False
    encryption_at_rest_guidance_provided: bool = False
    retention_enforcement_implemented: bool = False
    full_audit_log_implemented: bool = False
    notifications_implemented: bool = False
    live_operation_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_connection_attempted: bool = False
    scanner_attempted: bool = False
    notification_attempted: bool = False
    deployment_attempted: bool = False
    release_attempted: bool = False
    package_build_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    raw_payloads_exposed: bool = False
    raw_logs_exposed: bool = False
    urls_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    storage_keys_exposed: bool = False
    attachment_contents_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    controls: list[SecurityGapControl] = Field(default_factory=list)
    domain_items: list[SecurityGapItem] = Field(default_factory=list)
    policy_implementation_matrix: list[PolicyImplementationMatrixItem] = Field(default_factory=list)
    private_security_actions: list[PrivateSecurityActionItem] = Field(default_factory=list)
    privacy_template_sections: list[PrivacyTemplateSection] = Field(default_factory=list)
    encryption_guidance_items: list[EncryptionGuidanceItem] = Field(default_factory=list)
    known_limitations: list[KnownLimitationItem] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class SecurityGapCloseoutArtifactResult(BaseModel):
    status: SecurityGapCloseoutStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    external_operations: bool = False
    approval_operations: bool = False
    encryption_operations: bool = False
    deletion_operations: bool = False
    notification_operations: bool = False
