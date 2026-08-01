from enum import StrEnum

from pydantic import BaseModel, Field


class InfraSecurityReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class InfraSecurityDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "infra_security_ready_for_security_review"
    NEEDS_REVIEW = "infra_security_needs_review"
    BLOCKED = "infra_security_blocked"
    NOT_RUN = "infra_security_not_run"


class InfraSecurityCategory(StrEnum):
    SECRET_REFERENCE_HANDLING = "secret_reference_handling"
    SECRET_VALUE_EXCLUSION = "secret_value_exclusion"
    SECRET_PROVIDER_GATING = "secret_provider_gating"
    ADMIN_TOKEN_BOUNDARY = "admin_token_boundary"
    WEBHOOK_SECRET_BOUNDARY = "webhook_secret_boundary"
    DMSA_CREDENTIAL_BOUNDARY = "dmsa_credential_boundary"
    DATABASE_URL_BOUNDARY = "database_url_boundary"
    LOCAL_FILE_SECRET_BOUNDARY = "local_file_secret_boundary"
    CLOUD_SECRET_PROVIDER_BOUNDARY = "cloud_secret_provider_boundary"
    STORAGE_METADATA_BOUNDARY = "storage_metadata_boundary"
    ATTACHMENT_STORAGE_BOUNDARY = "attachment_storage_boundary"
    CLOUD_STORAGE_PROVIDER_BOUNDARY = "cloud_storage_provider_boundary"
    DATABASE_RUNTIME_BOUNDARY = "database_runtime_boundary"
    MIGRATION_BOUNDARY = "migration_boundary"
    BACKUP_RESTORE_BOUNDARY = "backup_restore_boundary"
    DIAGNOSTICS_MASKING_BOUNDARY = "diagnostics_masking_boundary"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"
    PRIVATE_WORKSPACE_BOUNDARY = "private_workspace_boundary"


class SecretBoundary(StrEnum):
    ENV_SECRET_REFERENCE = "env_secret_reference"
    LOCAL_FILE_SECRET_REFERENCE = "local_file_secret_reference"
    ADMIN_TOKEN_REFERENCE = "admin_token_reference"
    WEBHOOK_SIGNATURE_SECRET_REFERENCE = "webhook_signature_secret_reference"
    DMSA_CLIENT_ID_REFERENCE = "dmsa_client_id_reference"
    DMSA_CLIENT_SECRET_REFERENCE = "dmsa_client_secret_reference"
    DATABASE_URL_REFERENCE = "database_url_reference"
    AWS_SECRET_REFERENCE = "aws_secret_reference"
    AZURE_KEY_VAULT_REFERENCE = "azure_key_vault_reference"
    GCP_SECRET_REFERENCE = "gcp_secret_reference"
    DISABLED_SECRET_PROVIDER = "disabled_secret_provider"
    EXTERNAL_PLACEHOLDER_PROVIDER = "external_placeholder_provider"


class StorageBoundary(StrEnum):
    DISABLED_STORAGE_PROVIDER = "disabled_storage_provider"
    LOCAL_METADATA_STORAGE = "local_metadata_storage"
    TEST_STORAGE_PROVIDER = "test_storage_provider"
    ATTACHMENT_MANIFEST_METADATA = "attachment_manifest_metadata"
    CLOUD_STORAGE_REFERENCE = "cloud_storage_reference"
    S3_STORAGE_BOUNDARY = "s3_storage_boundary"
    AZURE_BLOB_STORAGE_BOUNDARY = "azure_blob_storage_boundary"
    GCS_STORAGE_BOUNDARY = "gcs_storage_boundary"
    PRESIGNED_URL_EXCLUSION = "presigned_url_exclusion"
    STORAGE_KEY_EXCLUSION = "storage_key_exclusion"


class DatabaseBoundary(StrEnum):
    SQLITE_DEMO_BOUNDARY = "sqlite_demo_boundary"
    POSTGRES_URL_REFERENCE_BOUNDARY = "postgres_url_reference_boundary"
    POSTGRES_CONNECTIVITY_GATE = "postgres_connectivity_gate"
    MIGRATION_PLAN_BOUNDARY = "migration_plan_boundary"
    BACKUP_PLAN_BOUNDARY = "backup_plan_boundary"
    RESTORE_PLAN_BOUNDARY = "restore_plan_boundary"
    EXTERNAL_DB_CONNECTION_BLOCKED_BY_DEFAULT = "external_db_connection_blocked_by_default"
    DB_DUMP_EXCLUSION = "db_dump_exclusion"


class InfraSecurityFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class InfraSecurityControl(BaseModel):
    name: str
    evidence_path: str
    description: str
    implemented: bool = True


class InfraSecurityScenario(BaseModel):
    category: InfraSecurityCategory
    expectation: str


class InfraProviderMatrixItem(BaseModel):
    provider: str
    boundary: str
    enabled_by_default: bool = False
    external_access_attempted: bool = False
    values_exposed: bool = False


class InfraSecurityReviewReport(BaseModel):
    status: InfraSecurityReviewStatus
    decision: InfraSecurityDecision
    categories: list[InfraSecurityCategory]
    secret_boundaries: list[SecretBoundary]
    storage_boundaries: list[StorageBoundary]
    database_boundaries: list[DatabaseBoundary]
    controls: list[InfraSecurityControl]
    scenarios: list[InfraSecurityScenario]
    provider_matrix: list[InfraProviderMatrixItem]
    categories_total: int
    secret_boundaries_total: int
    storage_boundaries_total: int
    database_boundaries_total: int
    provider_matrix_items_total: int
    findings: list[InfraSecurityFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    secret_values_exposed: bool = False
    secret_retrieval_attempted: bool = False
    storage_access_attempted: bool = False
    presigned_urls_exposed: bool = False
    storage_keys_exposed: bool = False
    db_connection_attempted: bool = False
    migration_attempted: bool = False
    backup_attempted: bool = False
    restore_attempted: bool = False
    dump_inspection_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    signed_urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    legal_compliance_claimed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class InfraSecurityArtifactResult(BaseModel):
    status: InfraSecurityReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    secret_retrieval: bool = False
    storage_access: bool = False
    database_operations: bool = False
