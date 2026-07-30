from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PostgresRuntimeStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"
    SUCCESS = "success"
    FAILED = "failed"
    DEPENDENCY_MISSING = "dependency_missing"


class PostgresRuntimeDecision(StrEnum):
    ALLOW_OFFLINE = "allow_offline"
    ALLOW_MANUAL = "allow_manual"
    REFUSE = "refuse"


class PostgresRuntimeFinding(StrictRuntimeModel):
    code: str
    status: PostgresRuntimeStatus
    message: str


class PostgresRuntimeRequirement(StrictRuntimeModel):
    name: str
    required: bool
    configured: bool
    private_reference: str = ""


class PostgresPoolConfigSummary(StrictRuntimeModel):
    pool_size: int
    max_overflow: int
    pool_timeout_seconds: int
    pool_recycle_seconds: int
    pool_pre_ping: bool
    connection_timeout_seconds: int
    statement_timeout_seconds: int
    ssl_required: bool
    sensitive_fields_included: bool = False


class PostgresConnectivityCheckResult(StrictRuntimeModel):
    operation: str = "connectivity"
    status: PostgresRuntimeStatus
    success: bool = False
    message: str
    cloud_or_external_db_contact_attempted: bool = False
    read_only_probe: bool = True
    migration_executed: bool = False
    backup_or_restore_executed: bool = False
    db_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    database_names_exposed: bool = False
    usernames_exposed: bool = False
    query_text_exposed: bool = False
    raw_logs_exposed: bool = False
    dump_or_backup_contents_exposed: bool = False
    private_paths_exposed: bool = False


class PostgresMigrationExecutionPlan(StrictRuntimeModel):
    status: PostgresRuntimeStatus
    decision: PostgresRuntimeDecision
    requirements: list[PostgresRuntimeRequirement]
    steps: list[str]
    migration_executed: bool = False
    external_contact_attempted: bool = False
    private_data_exposed: bool = False


class PostgresBackupVerificationPlan(StrictRuntimeModel):
    status: PostgresRuntimeStatus
    decision: PostgresRuntimeDecision
    requirements: list[PostgresRuntimeRequirement]
    steps: list[str]
    backup_files_inspected: bool = False
    backup_executed: bool = False
    external_contact_attempted: bool = False
    private_data_exposed: bool = False


class PostgresRestoreDrillPlan(StrictRuntimeModel):
    status: PostgresRuntimeStatus
    decision: PostgresRuntimeDecision
    requirements: list[PostgresRuntimeRequirement]
    steps: list[str]
    dump_or_backup_contents_inspected: bool = False
    restore_executed: bool = False
    external_contact_attempted: bool = False
    private_data_exposed: bool = False


class PostgresRuntimeReport(StrictRuntimeModel):
    status: PostgresRuntimeStatus
    decision: PostgresRuntimeDecision
    runtime_enabled: bool
    connectivity_enabled: bool
    migrations_enabled: bool
    backup_check_enabled: bool
    restore_check_enabled: bool
    cloud_or_external_db_contact_attempted: bool = False
    db_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    database_names_exposed: bool = False
    usernames_exposed: bool = False
    query_text_exposed: bool = False
    raw_logs_exposed: bool = False
    dump_or_backup_contents_exposed: bool = False
    private_paths_exposed: bool = False
    pool_config_summary: PostgresPoolConfigSummary
    findings: list[PostgresRuntimeFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class PostgresRuntimeArtifactResult(StrictRuntimeModel):
    files: list[str]
    written: bool
    raw_material_written: bool = False
    private_data_exposed: bool = False
