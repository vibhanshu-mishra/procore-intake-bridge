from enum import StrEnum

from pydantic import BaseModel, Field


class VersionPrepStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class VersionPrepDecision(StrEnum):
    READY_FOR_RELEASE_CANDIDATE_REVIEW = "version_prep_ready_for_release_candidate_review"
    NEEDS_REVIEW = "version_prep_needs_review"
    BLOCKED = "version_prep_blocked"
    NOT_RUN = "version_prep_not_run"


class VersionSourceType(StrEnum):
    APP_VERSION_FILE = "app_version_file"
    PYPROJECT_PROJECT_VERSION = "pyproject_project_version"
    CHANGELOG_ENTRY = "changelog_entry"
    DOCS_PROJECT_STATUS = "docs_project_status"
    RELEASE_READINESS = "release_readiness"
    PACKAGE_METADATA = "package_metadata"
    UNKNOWN = "unknown"


class PackageMetadataStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    PLACEHOLDER = "placeholder"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class ReleaseBoundaryStatus(StrEnum):
    DOCUMENTED = "documented"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class VersionPrepFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    source: str | None = None


class VersionSourceItem(BaseModel):
    source_type: VersionSourceType
    source: str
    version: str
    present: bool
    consistent_with_target: bool
    description: str


class PackageMetadataItem(BaseModel):
    name: str
    value: str
    status: PackageMetadataStatus
    source: str
    required: bool = False
    description: str = ""


class ReleaseBoundaryChecklistItem(BaseModel):
    code: str
    description: str
    status: ReleaseBoundaryStatus
    evidence: str
    operation_attempted: bool = False


class VersionReadinessMatrixItem(BaseModel):
    area: str
    status: str
    evidence: str
    limitation: str
    ready_for_candidate_review: bool


class VersionPrepReport(BaseModel):
    status: VersionPrepStatus
    decision: VersionPrepDecision
    target_version: str
    version_sources: list[VersionSourceItem] = Field(default_factory=list)
    package_metadata: list[PackageMetadataItem] = Field(default_factory=list)
    release_boundary_checklist: list[ReleaseBoundaryChecklistItem] = Field(
        default_factory=list
    )
    readiness_matrix: list[VersionReadinessMatrixItem] = Field(default_factory=list)
    version_sources_total: int
    package_metadata_items_total: int
    release_boundary_items_total: int
    findings: list[VersionPrepFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    version_source_present: bool
    package_metadata_present: bool
    changelog_entry_present: bool
    release_boundary_documented: bool
    package_build_attempted: bool = False
    docker_build_attempted: bool = False
    publish_attempted: bool = False
    tag_attempted: bool = False
    release_attempted: bool = False
    deploy_attempted: bool = False
    workflow_changed: bool = False
    github_api_attempted: bool = False
    package_registry_call_attempted: bool = False
    external_call_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    production_approval_claimed: bool = False
    release_approval_claimed: bool = False
    pilot_approval_claimed: bool = False
    deployment_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class VersionPrepArtifactResult(BaseModel):
    status: VersionPrepStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    package_build: bool = False
    docker_build: bool = False
    publish: bool = False
    tag: bool = False
    release: bool = False
    deploy: bool = False
