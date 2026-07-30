from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class StrictSmokeUxModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SandboxSmokeUxStatus(StrEnum):
    READY_FOR_PRIVATE_CONFIGURATION = "ready_for_private_configuration"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"


class SandboxSmokeUxFinding(StrictSmokeUxModel):
    code: str
    status: SandboxSmokeUxStatus
    message: str
    fail_level: bool = False


class SandboxSmokeUxRequirement(StrictSmokeUxModel):
    name: str
    configured: bool
    required_for_live_run: bool = True
    guidance: str


class SandboxSmokeUxChecklist(StrictSmokeUxModel):
    status: SandboxSmokeUxStatus
    requirements: tuple[SandboxSmokeUxRequirement, ...]
    findings: tuple[SandboxSmokeUxFinding, ...]
    external_calls: bool = False
    procore_calls: bool = False
    credentials_resolved: bool = False


class SandboxSmokeOutputPolicy(StrictSmokeUxModel):
    sanitized_summary_only: bool = True
    raw_payloads: bool = False
    raw_urls: bool = False
    raw_identifiers: bool = False
    attachment_downloads: bool = False
    private_result_refs_outside_git: bool = True
    guidance: str


class SandboxSmokeCommandSummary(StrictSmokeUxModel):
    planning_command: str
    live_command_name: str
    confirmation_phrase: str
    manually_gated: bool = True
    read_only: bool = True
    included_in_quality: bool = False
    included_in_prepare_sandbox: bool = False


class SandboxSmokeEvidenceRefTemplate(StrictSmokeUxModel):
    smoke_ref: str
    run_label: str
    company_scope_ref: str
    project_scope_ref: str
    result_status: str
    reviewer_placeholder: str
    expiry_placeholder: str
    report_contents_included: bool = False
    private_only: bool = True


class SandboxSmokeUxPlan(StrictSmokeUxModel):
    status: SandboxSmokeUxStatus
    summary: str
    checklist: SandboxSmokeUxChecklist
    command: SandboxSmokeCommandSummary
    output_policy: SandboxSmokeOutputPolicy
    what_it_checks: tuple[str, ...]
    what_it_does_not_do: tuple[str, ...]
