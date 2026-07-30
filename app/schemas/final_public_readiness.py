from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictFinalPublicReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinalPublicReadinessStatus(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "ready_for_maintainer_review"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    PASSED = "passed"
    WARNING = "warning"


class FinalPublicReadinessDecision(StrEnum):
    READY = "public_repo_ready_for_maintainer_review"
    NEEDS_REVIEW = "public_repo_needs_review"
    BLOCKED = "public_repo_blocked"
    NOT_RUN = "public_repo_not_run"


class FinalPublicReadinessCategory(StrEnum):
    REPOSITORY_STRUCTURE = "repository_structure"
    CLONE_TO_DEMO = "clone_to_demo"
    COMMAND_UX = "command_ux"
    DOCUMENTATION = "documentation"
    DOCS_SITE = "docs_site"
    EXAMPLES = "examples"
    FIXTURES = "fixtures"
    PUBLIC_SAFETY = "public_safety"
    ROUTE_SAFETY = "route_safety"
    SECRET_SAFETY = "secret_safety"
    STORAGE_SAFETY = "storage_safety"
    DATABASE_SAFETY = "database_safety"
    WEBHOOK_SAFETY = "webhook_safety"
    HOSTED_DEPLOYMENT_SAFETY = "hosted_deployment_safety"
    HTTPS_WEBHOOK_PLANNING_SAFETY = "https_webhook_planning_safety"
    HOSTED_PILOT_DRY_RUN_SAFETY = "hosted_pilot_dry_run_safety"
    GENERATED_OUTPUT_IGNORES = "generated_output_ignores"
    OPTIONAL_DEPENDENCIES = "optional_dependencies"
    LIVE_GATED_COMMANDS = "live_gated_commands"
    RELEASE_READINESS = "release_readiness"
    PUBLIC_PRIVATE_BOUNDARY = "public_private_boundary"
    KNOWN_LIMITATIONS = "known_limitations"
    MAINTAINER_REVIEW = "maintainer_review"


class FinalPublicReadinessFinding(StrictFinalPublicReadinessModel):
    category: FinalPublicReadinessCategory
    code: str
    severity: str
    message: str


class FinalPublicReadinessRequirement(StrictFinalPublicReadinessModel):
    category: FinalPublicReadinessCategory
    status: FinalPublicReadinessStatus
    checks_total: int
    checks_passed: int
    message: str


class FinalPublicReadinessReport(StrictFinalPublicReadinessModel):
    status: FinalPublicReadinessStatus
    decision: FinalPublicReadinessDecision
    categories_total: int
    categories_ready: int
    categories_needing_review: int
    categories_blocked: int
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks_attempted: list[str] = Field(default_factory=list)
    requirements: list[FinalPublicReadinessRequirement] = Field(default_factory=list)
    live_operation_attempted: bool = False
    external_call_attempted: bool = False
    deployment_attempted: bool = False
    release_attempted: bool = False
    procore_call_attempted: bool = False
    db_connection_attempted: bool = False
    cloud_call_attempted: bool = False
    webhook_registration_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    production_approval_claimed: bool = False
    findings: list[FinalPublicReadinessFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class FinalPublicReadinessArtifactResult(StrictFinalPublicReadinessModel):
    output_directory: str
    files: list[str]
    live_operations: bool = False
    release_attempted: bool = False
    deployment_attempted: bool = False
    private_values_exposed: bool = False
