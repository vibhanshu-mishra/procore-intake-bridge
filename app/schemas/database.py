from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictDatabaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatabaseProviderKind(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class DatabaseUrlSource(StrEnum):
    ENV = "env"
    FILE = "file"
    SECRET_PROVIDER = "secret_provider"


class DatabaseProviderStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"
    NOT_ATTEMPTED = "not_attempted"


class DatabaseFinding(StrictDatabaseModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class DatabaseReadinessReport(StrictDatabaseModel):
    provider: DatabaseProviderKind
    selected_mode: Literal["demo", "sandbox", "pilot"]
    status: DatabaseProviderStatus
    sqlite_allowed: bool
    postgres_allowed: bool
    external_connect_enabled: bool
    connectivity_attempted: bool = False
    migration_execution_ready: bool
    backup_plan_ready: bool
    rollback_plan_ready: bool
    findings: list[DatabaseFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    local_paths_exposed: bool = False
    external_calls: bool = False


class DatabaseConnectionPlan(StrictDatabaseModel):
    provider: DatabaseProviderKind
    selected_mode: Literal["demo", "sandbox", "pilot"]
    masked_url_ref: str
    url_source: DatabaseUrlSource
    external_connect_enabled: bool
    connectivity_attempted: bool = False
    steps: list[str]
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    external_calls: bool = False


class DatabaseMigrationPlan(StrictDatabaseModel):
    provider: DatabaseProviderKind
    selected_mode: Literal["demo", "sandbox", "pilot"]
    execution_ready: bool
    migration_executed: bool = False
    steps: list[str]
    command_placeholders: list[str]
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    local_paths_exposed: bool = False
    external_calls: bool = False


class DatabaseBackupPlan(StrictDatabaseModel):
    provider: DatabaseProviderKind
    ready: bool
    steps: list[str]
    backup_files_read: bool = False
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    local_paths_exposed: bool = False
    external_calls: bool = False


class DatabaseRestorePlan(DatabaseBackupPlan):
    restore_executed: bool = False
    dump_contents_read: bool = False


class DatabaseSafetyCheckResult(StrictDatabaseModel):
    success: bool
    status: DatabaseProviderStatus
    connectivity_attempted: bool
    query_read_only: bool = True
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    external_calls: bool = False


class DatabaseArtifactResult(StrictDatabaseModel):
    files: list[str]
    written: bool
    database_url_exposed: bool = False
    credentials_exposed: bool = False
    hostnames_exposed: bool = False
    local_paths_exposed: bool = False
