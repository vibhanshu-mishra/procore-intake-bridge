from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class StrictModeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UsageMode(StrEnum):
    DEMO = "demo"
    SANDBOX = "sandbox"
    PILOT = "pilot"


class UsageModeStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"


class UsageModeFinding(StrictModeModel):
    code: str
    status: UsageModeStatus
    message: str


class UsageModeRequirement(StrictModeModel):
    requirement: str
    satisfied: bool
    required: bool = True
    detail: str


class ModeQuickstartStep(StrictModeModel):
    order: int
    title: str
    instruction: str


class ModeCommandHint(StrictModeModel):
    mode: UsageMode
    purpose: str
    command: str
    may_call_procore: bool = False
    requires_explicit_gate: bool = False


class UsageModeReadiness(StrictModeModel):
    mode: UsageMode
    status: UsageModeStatus
    summary: str
    requirements: list[UsageModeRequirement]
    findings: list[UsageModeFinding]
    quickstart_steps: list[ModeQuickstartStep]
    command_hints: list[ModeCommandHint]
    secrets_required: bool
    external_services_required: bool
    automatic_procore_calls: bool = False
    values_exposed: bool = False
    local_paths_included: bool = False


class DemoModeReadiness(UsageModeReadiness):
    mode: UsageMode = UsageMode.DEMO


class SandboxModeReadiness(UsageModeReadiness):
    mode: UsageMode = UsageMode.SANDBOX
    smoke_test_manual: bool = True
    attachment_downloads_enabled: bool = False


class PilotModeReadiness(UsageModeReadiness):
    mode: UsageMode = UsageMode.PILOT
    private_evidence_required_in_repo: bool = False
    real_approval_recorded: bool = False


class UsageModeDoctorReport(StrictModeModel):
    generated_at: datetime
    selected_mode: UsageMode
    selected_mode_status: UsageModeStatus
    demo: DemoModeReadiness
    sandbox: SandboxModeReadiness
    pilot: PilotModeReadiness
    recommended_next_steps: list[str]
    command_hints: list[ModeCommandHint]
    safety_boundaries: list[str]
    values_exposed: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    file_contents_included: bool = False
    local_paths_included: bool = False


class ModeArtifactResult(StrictModeModel):
    selected_mode: UsageMode
    output_directory: str
    files: list[str]
    external_calls: bool = False
    procore_calls: bool = False
    file_contents_included: bool = False
    local_paths_included: bool = False
    values_exposed: bool = False
