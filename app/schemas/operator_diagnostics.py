from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticFinding(BaseModel):
    code: str
    severity: DiagnosticSeverity
    message: str


class DiagnosticSection(BaseModel):
    name: str
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)


class RuntimeDiagnosticSummary(BaseModel):
    environment: str
    app_version: str
    diagnostics_enabled: bool
    local_first: bool = True


class DependencyDiagnosticSummary(BaseModel):
    available: bool
    packages: dict[str, str] = Field(default_factory=dict)


class RouteDiagnosticSummary(BaseModel):
    available: bool
    total: int = 0
    method_counts: dict[str, int] = Field(default_factory=dict)
    routes: list[dict[str, Any]] = Field(default_factory=list)


class DatabaseDiagnosticSummary(BaseModel):
    available: bool
    table_counts: dict[str, int] = Field(default_factory=dict)
    rows_included: bool = False


class QueueDiagnosticSummary(BaseModel):
    available: bool
    pending: int = 0
    failed: int = 0
    done: int = 0
    skipped: int = 0
    rows_included: bool = False


class ConfigurationDiagnosticSummary(BaseModel):
    available: bool
    posture: dict[str, Any] = Field(default_factory=dict)
    environment_values_included: bool = False


class SafetyDiagnosticSummary(BaseModel):
    read_only_procore: bool = True
    procore_writes: bool = False
    raw_logs_included: bool = False
    database_file_included: bool = False
    attachments_included: bool = False
    payloads_included: bool = False


class RedactionDiagnosticSummary(BaseModel):
    strict: bool
    redacted_count: int = 0
    safe: bool = True
    patterns_detected: list[str] = Field(default_factory=list)


class OperatorDiagnosticsReport(BaseModel):
    generated_at: datetime
    environment: str
    app_version: str
    diagnostics_enabled: bool
    values_exposed: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    file_contents_included: bool = False
    raw_payloads_included: bool = False
    local_paths_included: bool = False
    runtime: RuntimeDiagnosticSummary
    dependencies: DependencyDiagnosticSummary
    routes: RouteDiagnosticSummary
    database: DatabaseDiagnosticSummary
    queue: QueueDiagnosticSummary
    configuration: ConfigurationDiagnosticSummary
    safety: SafetyDiagnosticSummary
    sections: list[DiagnosticSection] = Field(default_factory=list)
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    redaction: RedactionDiagnosticSummary


class SupportBundleRequest(BaseModel):
    include_markdown: bool = True
    include_json: bool = True


class SupportBundleFileManifestItem(BaseModel):
    name: str
    size_bytes: int
    sha256: str
    sanitized: bool = True


class SupportBundleResult(BaseModel):
    output_directory: str
    files: list[str]
    manifest: list[SupportBundleFileManifestItem]
    external_calls: bool = False
    sensitive_values_included: bool = False


class SupportBundleRedactionReport(BaseModel):
    safe: bool
    files_checked: int
    issues_count: int
    issue_types: list[str] = Field(default_factory=list)
