from enum import StrEnum

from pydantic import BaseModel, Field


class DocsSitePolishStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class DocsSiteDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "docs_site_ready_for_maintainer_review"
    NEEDS_REVIEW = "docs_site_needs_review"
    BLOCKED = "docs_site_blocked"
    NOT_RUN = "docs_site_not_run"


class DocsAudiencePath(StrEnum):
    FIRST_TIME_EVALUATOR = "first_time_evaluator"
    DEMO_USER = "demo_user"
    SANDBOX_PREPARER = "sandbox_preparer"
    PILOT_PREPARER = "pilot_preparer"
    HOSTED_PREPARER = "hosted_preparer"
    SECURITY_REVIEWER = "security_reviewer"
    OPERATOR_USER = "operator_user"
    MAINTAINER_RELEASE_REVIEWER = "maintainer_release_reviewer"
    DEVELOPER_CONTRIBUTOR = "developer_contributor"


class DocsNavigationGroup(StrEnum):
    START_HERE = "start_here"
    SETUP_AND_DEMO = "setup_and_demo"
    PRODUCT_UI = "product_ui"
    API_REFERENCE = "api_reference"
    OPERATIONS = "operations"
    SANDBOX_AND_PILOT = "sandbox_and_pilot"
    HOSTED_PREPARATION = "hosted_preparation"
    SECURITY_AND_READINESS = "security_and_readiness"
    RELEASE_AND_MAINTENANCE = "release_and_maintenance"
    EXAMPLES_AND_WALKTHROUGHS = "examples_and_walkthroughs"


class DocsPageClass(StrEnum):
    LANDING = "landing"
    SETUP = "setup"
    DEMO = "demo"
    PRODUCT = "product"
    API = "api"
    OPERATIONS = "operations"
    SECURITY = "security"
    HOSTED = "hosted"
    RELEASE = "release"
    REFERENCE = "reference"
    EXAMPLE = "example"
    UNKNOWN = "unknown"


class DocsSiteFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    document: str | None = None


class DocsPageItem(BaseModel):
    path: str
    title: str
    page_class: DocsPageClass
    navigation_group: DocsNavigationGroup
    in_mkdocs_nav: bool = False
    core_document: bool = False


class DocsReaderPathItem(BaseModel):
    audience: DocsAudiencePath
    title: str
    description: str
    documents: list[str]
    local_only: bool = True


class DocsNavigationMapItem(BaseModel):
    group: DocsNavigationGroup
    label: str
    document: str
    page_class: DocsPageClass
    order: int
    target_exists: bool = True


class DocsLinkInventoryItem(BaseModel):
    source: str
    label: str
    target: str
    internal: bool = True
    target_exists: bool
    anchor_only: bool = False


class DocsSiteChecklistItem(BaseModel):
    code: str
    description: str
    passed: bool
    evidence: str
    blocker: bool = False


class DocsSitePolishReport(BaseModel):
    status: DocsSitePolishStatus
    decision: DocsSiteDecision
    pages: list[DocsPageItem] = Field(default_factory=list)
    reader_paths: list[DocsReaderPathItem] = Field(default_factory=list)
    navigation_map: list[DocsNavigationMapItem] = Field(default_factory=list)
    link_inventory: list[DocsLinkInventoryItem] = Field(default_factory=list)
    checklist: list[DocsSiteChecklistItem] = Field(default_factory=list)
    docs_total: int
    nav_groups_total: int
    audience_paths_total: int
    checklist_items_total: int
    findings: list[DocsSiteFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    local_only: bool = True
    mkdocs_config_present: bool
    nav_structure_present: bool
    reader_paths_present: bool
    local_preview_documented: bool
    hosting_automation_present: bool = False
    external_analytics_present: bool = False
    external_assets_present: bool = False
    docs_deploy_attempted: bool = False
    external_call_attempted: bool = False
    github_api_attempted: bool = False
    package_build_attempted: bool = False
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
    deployment_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class DocsSiteArtifactResult(BaseModel):
    status: DocsSitePolishStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    docs_deployment: bool = False
    external_operations: bool = False
