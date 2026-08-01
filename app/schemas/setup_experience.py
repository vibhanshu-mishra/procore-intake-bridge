from enum import StrEnum

from pydantic import BaseModel, Field


class SetupExperienceStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class SetupExperienceDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "setup_experience_ready_for_maintainer_review"
    NEEDS_REVIEW = "setup_experience_needs_review"
    BLOCKED = "setup_experience_blocked"
    NOT_RUN = "setup_experience_not_run"


class SetupExperienceStep(StrEnum):
    REPOSITORY_LOCATION = "repository_location"
    PYTHON_PREREQUISITES = "python_prerequisites"
    VIRTUAL_ENVIRONMENT = "virtual_environment"
    DEPENDENCY_INSTALL = "dependency_install"
    ENVIRONMENT_FILE = "environment_file"
    DEMO_MODE = "demo_mode"
    LOCAL_DATABASE = "local_database"
    LOCAL_APP_START = "local_app_start"
    PRODUCT_DASHBOARD = "product_dashboard"
    SAFETY_CHECKS = "safety_checks"
    DOCS_SITE = "docs_site"
    SANDBOX_BOUNDARY = "sandbox_boundary"
    PILOT_BOUNDARY = "pilot_boundary"
    HOSTED_BOUNDARY = "hosted_boundary"
    TROUBLESHOOTING = "troubleshooting"


class SetupExperienceFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    step: SetupExperienceStep | None = None


class SetupPrerequisite(BaseModel):
    name: str
    step: SetupExperienceStep
    required: bool = True
    available: bool | None = None
    check_command: str
    guidance: str


class SetupCommand(BaseModel):
    name: str
    step: SetupExperienceStep
    command: str
    description: str
    sequence: int | None = None
    local_only: bool = True
    requires_secrets: bool = False
    performs_live_operation: bool = False


class SetupTroubleshootingItem(BaseModel):
    code: str
    symptom: str
    guidance: str
    check_command: str | None = None


class SetupModePath(BaseModel):
    mode: str
    description: str
    first_command: str
    gated: bool = False
    requires_secrets: bool = False
    local_only: bool = True


class SetupCommandMapItem(BaseModel):
    step: SetupExperienceStep
    purpose: str
    command: str
    mode: str = "local"
    sequence: int | None = None


class SetupExperienceReport(BaseModel):
    status: SetupExperienceStatus
    decision: SetupExperienceDecision
    prerequisites_total: int
    commands_total: int
    mode_paths_total: int
    findings: list[SetupExperienceFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    setup_is_local_only: bool = True
    demo_safe_defaults_required: bool = True
    secrets_required_for_demo: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    package_build_attempted: bool = False
    publish_attempted: bool = False
    release_attempted: bool = False
    deploy_attempted: bool = False
    workflow_changed: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    production_approval_claimed: bool = False
    release_approval_claimed: bool = False
    pilot_approval_claimed: bool = False
    prerequisites: list[SetupPrerequisite] = Field(default_factory=list)
    commands: list[SetupCommand] = Field(default_factory=list)
    mode_paths: list[SetupModePath] = Field(default_factory=list)
    troubleshooting_items: list[SetupTroubleshootingItem] = Field(default_factory=list)
    command_map: list[SetupCommandMapItem] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class SetupExperienceArtifactResult(BaseModel):
    status: SetupExperienceStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    external_operations: bool = False
    package_build_operations: bool = False
    publish_operations: bool = False
    release_operations: bool = False
    deployment_operations: bool = False
