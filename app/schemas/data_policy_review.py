from enum import StrEnum

from pydantic import BaseModel, Field


class DataPolicyReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class DataPolicyDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "data_policy_ready_for_security_review"
    NEEDS_REVIEW = "data_policy_needs_review"
    BLOCKED = "data_policy_blocked"
    NOT_RUN = "data_policy_not_run"


class DataClassification(StrEnum):
    PUBLIC_PLACEHOLDER = "public_placeholder"
    LOCAL_DEMO_METADATA = "local_demo_metadata"
    LOCAL_RUNTIME_METADATA = "local_runtime_metadata"
    PRIVATE_CONFIGURATION_REFERENCE = "private_configuration_reference"
    SECRET_REFERENCE = "secret_reference"
    WEBHOOK_PAYLOAD_BOUNDARY = "webhook_payload_boundary"
    ATTACHMENT_METADATA = "attachment_metadata"
    ATTACHMENT_CONTENT_EXCLUDED = "attachment_content_excluded"
    EXPORT_SUMMARY_METADATA = "export_summary_metadata"
    DIAGNOSTICS_SUMMARY_METADATA = "diagnostics_summary_metadata"
    PRIVATE_EVIDENCE_REFERENCE = "private_evidence_reference"
    GENERATED_OUTPUT = "generated_output"
    FORBIDDEN_PUBLIC_CONTENT = "forbidden_public_content"


class DataRetentionBoundary(StrEnum):
    PUBLIC_REPOSITORY = "public_repository"
    LOCAL_DEMO_SQLITE = "local_demo_sqlite"
    LOCAL_POSTGRES_RUNTIME = "local_postgres_runtime"
    WEBHOOK_EVENT_QUEUE = "webhook_event_queue"
    ATTACHMENT_MANIFEST_METADATA = "attachment_manifest_metadata"
    LIFECYCLE_EVENT_HISTORY = "lifecycle_event_history"
    OPERATOR_EXPORTS = "operator_exports"
    DIAGNOSTICS_OUTPUT = "diagnostics_output"
    SUPPORT_BUNDLE_OUTPUT = "support_bundle_output"
    SANDBOX_EVIDENCE_REFERENCES = "sandbox_evidence_references"
    PILOT_EVIDENCE_WORKSPACE = "pilot_evidence_workspace"
    GENERATED_OUTPUT_DIRECTORIES = "generated_output_directories"
    PRIVATE_WORKSPACE = "private_workspace"
    CLOUD_SECRET_REFERENCE_BOUNDARY = "cloud_secret_reference_boundary"
    CLOUD_STORAGE_METADATA_BOUNDARY = "cloud_storage_metadata_boundary"


class DataRedactionBoundary(StrEnum):
    RAW_PAYLOAD_REDACTION = "raw_payload_redaction"
    SECRET_REDACTION = "secret_redaction"
    URL_REDACTION = "url_redaction"
    SIGNED_URL_REDACTION = "signed_url_redaction"
    PRIVATE_PATH_REDACTION = "private_path_redaction"
    STORAGE_KEY_REDACTION = "storage_key_redaction"
    ORIGINAL_FILENAME_REDACTION = "original_filename_redaction"
    ATTACHMENT_CONTENT_EXCLUSION = "attachment_content_exclusion"
    SOURCE_IDENTIFIER_MASKING = "source_identifier_masking"
    ACTOR_IDENTITY_HASHING = "actor_identity_hashing"
    DIAGNOSTIC_ERROR_SANITIZATION = "diagnostic_error_sanitization"
    CSV_FORMULA_NEUTRALIZATION = "csv_formula_neutralization"


class DataPolicyFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class DataPolicyControl(BaseModel):
    name: str
    evidence_path: str
    description: str
    implemented: bool = True


class DataPolicyScenario(BaseModel):
    classification: DataClassification
    retention_boundary: DataRetentionBoundary
    redaction_boundary: DataRedactionBoundary
    expectation: str


class DataRetentionItem(BaseModel):
    boundary: DataRetentionBoundary
    classification: DataClassification
    public_handling: str
    private_review_required: bool = False


class GeneratedOutputInventoryItem(BaseModel):
    pattern: str
    classification: DataClassification = DataClassification.GENERATED_OUTPUT
    ignored: bool = True
    content_excluded: bool = True


class DataPolicyReviewReport(BaseModel):
    status: DataPolicyReviewStatus
    decision: DataPolicyDecision
    classifications: list[DataClassification]
    retention_boundaries: list[DataRetentionItem]
    redaction_boundaries: list[DataRedactionBoundary]
    controls: list[DataPolicyControl]
    scenarios: list[DataPolicyScenario]
    generated_output_inventory: list[GeneratedOutputInventoryItem]
    classifications_total: int
    retention_boundaries_total: int
    redaction_boundaries_total: int
    generated_output_patterns_total: int
    findings: list[DataPolicyFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    destructive_deletion_implemented: bool = False
    live_scan_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    raw_payloads_exposed: bool = False
    urls_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    storage_keys_exposed: bool = False
    original_filenames_exposed: bool = False
    attachment_contents_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    legal_compliance_claimed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class DataPolicyArtifactResult(BaseModel):
    status: DataPolicyReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    deletion_operations: bool = False
