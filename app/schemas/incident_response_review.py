from enum import StrEnum

from pydantic import BaseModel, Field


class IncidentResponseReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class IncidentResponseDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "incident_response_ready_for_security_review"
    NEEDS_REVIEW = "incident_response_needs_review"
    BLOCKED = "incident_response_blocked"
    NOT_RUN = "incident_response_not_run"


class IncidentCategory(StrEnum):
    SECRET_EXPOSURE = "secret_exposure"
    ADMIN_AUTH_FAILURE = "admin_auth_failure"
    WEBHOOK_SIGNATURE_FAILURE = "webhook_signature_failure"
    SUSPECTED_WEBHOOK_REPLAY = "suspected_webhook_replay"
    GENERATED_OUTPUT_LEAK = "generated_output_leak"
    PUBLIC_REPO_SECRET_LEAK = "public_repo_secret_leak"
    PRIVATE_WORKSPACE_LEAK = "private_workspace_leak"
    ATTACHMENT_METADATA_EXPOSURE = "attachment_metadata_exposure"
    RAW_PAYLOAD_EXPOSURE = "raw_payload_exposure"
    OPERATOR_EXPORT_EXPOSURE = "operator_export_exposure"
    DATABASE_CONFIGURATION_EXPOSURE = "database_configuration_exposure"
    STORAGE_BOUNDARY_FAILURE = "storage_boundary_failure"
    CLOUD_PROVIDER_MISCONFIGURATION = "cloud_provider_misconfiguration"
    DEPENDENCY_SUPPLY_CHAIN_ISSUE = "dependency_supply_chain_issue"
    SANDBOX_LIVE_OPERATION_INCIDENT = "sandbox_live_operation_incident"
    PILOT_EVIDENCE_HANDLING_INCIDENT = "pilot_evidence_handling_incident"
    DEPLOYMENT_ROLLBACK_SITUATION = "deployment_rollback_situation"
    DIAGNOSTICS_SUPPORT_BUNDLE_EXPOSURE = "diagnostics_support_bundle_exposure"
    PUBLIC_PRIVATE_BOUNDARY_ISSUE = "public_private_boundary_issue"


class IncidentSeverity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NEEDS_PRIVATE_ASSESSMENT = "needs_private_assessment"


class AuditLogBoundary(StrEnum):
    ROUTE_ACCESS_BOUNDARY = "route_access_boundary"
    WEBHOOK_EVENT_QUEUE_BOUNDARY = "webhook_event_queue_boundary"
    WEBHOOK_FINGERPRINT_BOUNDARY = "webhook_fingerprint_boundary"
    SYNC_RUN_HISTORY_BOUNDARY = "sync_run_history_boundary"
    INTAKE_RECORD_METADATA_BOUNDARY = "intake_record_metadata_boundary"
    LIFECYCLE_EVENT_HISTORY_BOUNDARY = "lifecycle_event_history_boundary"
    TRIAGE_SUMMARY_BOUNDARY = "triage_summary_boundary"
    ATTACHMENT_MANIFEST_METADATA_BOUNDARY = "attachment_manifest_metadata_boundary"
    OPERATOR_EXPORT_ARTIFACT_BOUNDARY = "operator_export_artifact_boundary"
    DIAGNOSTICS_SUMMARY_BOUNDARY = "diagnostics_summary_boundary"
    SUPPORT_BUNDLE_BOUNDARY = "support_bundle_boundary"
    MIGRATION_STATUS_BOUNDARY = "migration_status_boundary"
    DEPLOYMENT_READINESS_BOUNDARY = "deployment_readiness_boundary"
    SECRET_PROVIDER_INVENTORY_BOUNDARY = "secret_provider_inventory_boundary"
    STORAGE_PROVIDER_INVENTORY_BOUNDARY = "storage_provider_inventory_boundary"
    POSTGRES_RUNTIME_PLAN_BOUNDARY = "postgres_runtime_plan_boundary"
    PRIVATE_EVIDENCE_REFERENCE_BOUNDARY = "private_evidence_reference_boundary"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"


class ForensicsEvidenceType(StrEnum):
    PRIVATE_INCIDENT_TIMELINE_REFERENCE = "private_incident_timeline_reference"
    PRIVATE_LOG_REFERENCE = "private_log_reference"
    PRIVATE_SCREENSHOT_REFERENCE = "private_screenshot_reference"
    PRIVATE_CONFIG_SNAPSHOT_REFERENCE = "private_config_snapshot_reference"
    PRIVATE_SECRET_ROTATION_REFERENCE = "private_secret_rotation_reference"
    PRIVATE_WEBHOOK_EVENT_REFERENCE = "private_webhook_event_reference"
    PRIVATE_DATABASE_REVIEW_REFERENCE = "private_database_review_reference"
    PRIVATE_STORAGE_REVIEW_REFERENCE = "private_storage_review_reference"
    PRIVATE_CLOUD_PROVIDER_REVIEW_REFERENCE = "private_cloud_provider_review_reference"
    PRIVATE_DEPENDENCY_REVIEW_REFERENCE = "private_dependency_review_reference"
    PRIVATE_NOTIFICATION_DECISION_REFERENCE = "private_notification_decision_reference"
    PRIVATE_ROLLBACK_DECISION_REFERENCE = "private_rollback_decision_reference"
    PUBLIC_REPO_COMMIT_REFERENCE = "public_repo_commit_reference"
    GENERATED_OUTPUT_REFERENCE = "generated_output_reference"
    PLACEHOLDER_ONLY = "placeholder_only"


class IncidentResponseFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class IncidentResponseControl(BaseModel):
    name: str
    evidence_path: str
    description: str
    implemented: bool = True


class IncidentResponseScenario(BaseModel):
    category: IncidentCategory
    severity: IncidentSeverity
    expectation: str


class IncidentRunbookItem(BaseModel):
    category: IncidentCategory
    action: str
    private_review_required: bool = True


class IncidentScenarioMatrixItem(BaseModel):
    category: IncidentCategory
    severity: IncidentSeverity
    evidence_type: ForensicsEvidenceType
    placeholder_only: bool = True


class IncidentResponseReviewReport(BaseModel):
    status: IncidentResponseReviewStatus
    decision: IncidentResponseDecision
    categories: list[IncidentCategory]
    severities: list[IncidentSeverity]
    audit_log_boundaries: list[AuditLogBoundary]
    forensics_evidence_types: list[ForensicsEvidenceType]
    controls: list[IncidentResponseControl]
    scenarios: list[IncidentResponseScenario]
    runbook: list[IncidentRunbookItem]
    scenario_matrix: list[IncidentScenarioMatrixItem]
    categories_total: int
    severities_total: int
    audit_log_boundaries_total: int
    forensics_evidence_types_total: int
    scenario_matrix_items_total: int
    findings: list[IncidentResponseFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    live_incident_response_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_connection_attempted: bool = False
    scanner_attempted: bool = False
    notification_attempted: bool = False
    forensics_tool_attempted: bool = False
    log_collection_attempted: bool = False
    packet_capture_attempted: bool = False
    evidence_collection_attempted: bool = False
    deletion_or_purge_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    raw_logs_exposed: bool = False
    raw_payloads_exposed: bool = False
    live_headers_exposed: bool = False
    live_payloads_exposed: bool = False
    urls_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    storage_keys_exposed: bool = False
    attachment_contents_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    legal_compliance_claimed: bool = False
    breach_notification_claimed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class IncidentResponseArtifactResult(BaseModel):
    status: IncidentResponseReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    collection_operations: bool = False
    notification_operations: bool = False
