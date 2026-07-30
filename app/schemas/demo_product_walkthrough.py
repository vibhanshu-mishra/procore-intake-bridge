from enum import StrEnum

from pydantic import BaseModel, Field


class DemoWalkthroughStatus(StrEnum):
    AVAILABLE = "available"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


class DemoWalkthroughStepStatus(StrEnum):
    AVAILABLE = "available"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


class DemoWalkthroughFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class DemoWalkthroughStep(BaseModel):
    group: str
    title: str
    status: DemoWalkthroughStepStatus
    description: str
    commands: list[str] = Field(default_factory=list)
    docs: list[str] = Field(default_factory=list)
    findings: list[DemoWalkthroughFinding] = Field(default_factory=list)


class DemoWalkthroughChecklist(BaseModel):
    title: str
    items: list[str]
    fake_data_only: bool = True


class DemoWalkthroughReport(BaseModel):
    status: DemoWalkthroughStatus
    steps: list[DemoWalkthroughStep]
    checklist: DemoWalkthroughChecklist
    steps_total: int
    steps_ready: int
    steps_needing_review: int
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    demo_only: bool = True
    fake_data_required: bool = True
    live_operation_attempted: bool = False
    procore_call_attempted: bool = False
    external_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    cloud_call_attempted: bool = False
    deployment_attempted: bool = False
    release_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    approval_or_production_claimed: bool = False
    findings: list[DemoWalkthroughFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class DemoWalkthroughArtifactResult(BaseModel):
    status: DemoWalkthroughStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    external_calls_made: bool = False
