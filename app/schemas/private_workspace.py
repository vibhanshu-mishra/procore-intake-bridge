from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictWorkspaceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PrivateWorkspaceMode(StrEnum):
    SANDBOX = "sandbox"
    PILOT = "pilot"
    SANDBOX_AND_PILOT = "sandbox_and_pilot"


class PrivateWorkspaceSection(StrEnum):
    README = "README"
    ENVIRONMENT = "environment"
    SANDBOX = "sandbox"
    DMSA = "dmsa"
    PERMISSIONS = "permissions"
    WEBHOOKS = "webhooks"
    DIAGNOSTICS = "diagnostics"
    CUSTOMER_PROFILE = "customer_profile"
    EVIDENCE = "evidence"
    EVIDENCE_REVIEW = "evidence_review"
    PILOT_READINESS = "pilot_readiness"
    PILOT_APPROVAL = "pilot_approval"
    LAUNCH = "launch"
    ROLLBACK = "rollback"
    INCIDENT_RESPONSE = "incident_response"
    NOTES = "notes"


class PrivateWorkspaceFileSpec(StrictWorkspaceModel):
    relative_path: str
    section: PrivateWorkspaceSection
    purpose: str
    required_for_modes: list[PrivateWorkspaceMode]
    template_kind: Literal["markdown", "json", "env"]
    placeholder_only: bool = True
    contains_file_contents: bool = False
    contains_secret_values: bool = False
    notes: list[str] = Field(default_factory=list)


class PrivateWorkspaceManifest(StrictWorkspaceModel):
    schema_version: str = "1.0"
    workspace_name: str = "example-private-workspace"
    workspace_label: str = "Example Private Workspace"
    mode: PrivateWorkspaceMode
    files: list[PrivateWorkspaceFileSpec]
    notes: list[str] = Field(default_factory=list)
    placeholder_only: bool = True
    external_calls: bool = False
    procore_calls: bool = False
    file_contents_included: bool = False
    values_exposed: bool = False


class PrivateWorkspaceProfile(StrictWorkspaceModel):
    manifest: PrivateWorkspaceManifest
    output_root: str = "private-workspace"
    ignored_local_only: bool = True


class PrivateWorkspaceFinding(StrictWorkspaceModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str
    relative_path: str = ""


class PrivateWorkspaceValidationReport(StrictWorkspaceModel):
    generated_at: datetime
    workspace_name: str
    mode: PrivateWorkspaceMode
    valid: bool
    blocking_findings_count: int
    warning_findings_count: int
    file_count: int
    findings: list[PrivateWorkspaceFinding]
    external_calls: bool = False
    procore_calls: bool = False
    binary_files_read: bool = False
    files_outside_root_read: bool = False
    values_exposed: bool = False
    local_paths_included: bool = False


class PrivateWorkspaceArtifactResult(StrictWorkspaceModel):
    mode: PrivateWorkspaceMode
    output_directory: str
    files: list[str]
    overwritten: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    values_exposed: bool = False
    local_paths_included: bool = False


class PrivateWorkspaceSummary(StrictWorkspaceModel):
    enabled: bool
    output_root_sanitized: bool
    real_ids_blocked: bool
    real_identities_blocked: bool
    file_contents_blocked: bool
    absolute_paths_blocked: bool
    generated_workspace_ignored: bool
    validators_available: bool
    external_calls: bool = False
    values_exposed: bool = False
