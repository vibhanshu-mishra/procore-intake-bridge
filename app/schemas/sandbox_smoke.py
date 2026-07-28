from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SandboxSmokeFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str


class SandboxSmokeStepResult(BaseModel):
    name: str
    status: Literal["skipped", "passed", "failed", "blocked"]
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class SandboxSmokeReport(BaseModel):
    environment: str
    sandbox_only: bool = True
    live_mode_explicitly_enabled: bool
    max_records: int
    connection_id: int
    company_id_hash: str
    project_id_hash: str
    steps: list[SandboxSmokeStepResult]
    findings: list[SandboxSmokeFinding]
    generated_at: datetime


class SandboxSmokePlan(BaseModel):
    enabled: bool
    environment: str
    sandbox_only: bool = True
    confirmation_required: bool
    live_mode_required: bool = True
    attachment_downloads: bool = False
    raw_payload_persistence: bool = False
    procore_writes: bool = False
    max_records: int
    connection_configured: bool
    company_configured: bool
    project_configured: bool
    secret_references_resolved: bool = False
    warning: str
    steps: list[str]


class SandboxSmokeRequest(BaseModel):
    connection_id: int = Field(ge=1)
    company_id: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    confirmation_phrase: str
    max_records: int | None = Field(default=None, ge=1)
    write_report: bool | None = None


class SandboxSmokeConfigSummary(BaseModel):
    enabled: bool
    environment: str
    production_allowed: bool
    confirmation_required: bool
    confirmation_phrase_configured: bool
    live_mode_enabled: bool
    max_records: int
    attachment_downloads: bool
    write_report: bool
    output_root_configured: bool
    connection_configured: bool
    project_configured: bool
    company_configured: bool
