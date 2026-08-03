"""Public-safe models for the offline 0.1.0 release handoff.

The models intentionally describe a maintainer decision aid.  They do not
represent an actual package release, publication, deployment, or approval.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class VersionedReleaseHandoffStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class VersionedReleaseHandoffDecision(StrEnum):
    READY_FOR_MAINTAINER_DECISION = "versioned_release_ready_for_maintainer_decision"
    NEEDS_REVIEW = "versioned_release_needs_review"
    BLOCKED = "versioned_release_blocked"
    NOT_RUN = "versioned_release_not_run"


class VersionedReleaseDomain(StrEnum):
    RELEASE_CANDIDATE_REVIEW = "release_candidate_review"
    VERSION_METADATA = "version_metadata"
    PACKAGE_METADATA = "package_metadata"
    LOCAL_SETUP = "local_setup"
    DEMO_EXPERIENCE = "demo_experience"
    API_DOCUMENTATION = "api_documentation"
    HOSTED_UI_PREPARATION = "hosted_ui_preparation"
    DOCS_SITE = "docs_site"
    SECURITY_READINESS = "security_readiness"
    PUBLIC_SAFETY = "public_safety"
    ROUTE_BOUNDARY = "route_boundary"
    GENERATED_OUTPUT_BOUNDARY = "generated_output_boundary"
    CHANGELOG = "changelog"
    KNOWN_LIMITATIONS = "known_limitations"
    MAINTAINER_DECISION = "maintainer_decision"


class VersionedReleaseGateStatus(StrEnum):
    PASS = "pass"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class ReleaseNoteCategory(StrEnum):
    HIGHLIGHT = "highlight"
    SETUP = "setup"
    DEMO = "demo"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    BOUNDARY = "boundary"
    LIMITATION = "limitation"
    RELEASE_BOUNDARY = "boundary"
    KNOWN_LIMITATION = "limitation"


class IncludedScopeCategory(StrEnum):
    SETUP = "setup"
    DEMO = "demo"
    API = "api"
    HOSTED_UI = "hosted_ui"
    DOCS = "docs"
    SECURITY = "security"
    RELEASE_REVIEW = "release_review"
    SETUP_EXPERIENCE = "setup"
    DEMO_EXPERIENCE = "demo"
    API_DOCUMENTATION = "api"
    HOSTED_UI_PREPARATION = "hosted_ui"
    DOCS_SITE = "docs"
    VERSION_METADATA = "version_metadata"
    RELEASE_CANDIDATE_REVIEW = "release_review"


class KnownLimitationCategory(StrEnum):
    PRIVATE_REVIEW = "private_review"
    PRODUCTION_APPROVAL = "production_approval"
    HOSTED_DEPLOYMENT = "hosted_deployment"
    NOTIFICATIONS = "notifications"
    AUDIT_LOG = "audit_log"
    RETENTION = "retention"
    ENCRYPTION = "encryption"
    PRIVACY_LEGAL = "privacy_legal"
    NO_PRODUCTION_APPROVAL = "production_approval"
    NO_HOSTED_DEPLOYMENT = "hosted_deployment"
    NO_NOTIFICATION_SYSTEM = "notifications"
    NO_FULL_AUDIT_LOG = "audit_log"
    NO_RETENTION_ENFORCEMENT = "retention"
    NO_APP_LEVEL_ENCRYPTION = "encryption"
    NO_PRIVACY_LEGAL_COMPLIANCE = "privacy_legal"


class VersionedReleaseFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: VersionedReleaseDomain | None = None
    source: str | None = None


class VersionedReleaseDomainSummary(BaseModel):
    domain: VersionedReleaseDomain
    status: VersionedReleaseGateStatus
    summary: str
    source: str
    public_safe: bool = True
    private_review_required: bool = False


class VersionedReleaseGate(BaseModel):
    code: str
    domain: VersionedReleaseDomain
    status: VersionedReleaseGateStatus
    description: str
    evidence: list[str] = Field(default_factory=list)
    required: bool = True


class ReleaseNoteItem(BaseModel):
    category: ReleaseNoteCategory
    title: str
    summary: str
    source: str = "local repository"
    public_safe: bool = True


class ReleaseScopeItem(BaseModel):
    category: IncludedScopeCategory
    phase: str
    title: str
    summary: str
    source: str = "local repository"
    public_safe: bool = True


class KnownLimitationItem(BaseModel):
    category: KnownLimitationCategory
    title: str
    summary: str
    next_step: str
    private_review_required: bool = True


class MaintainerDecisionChecklistItem(BaseModel):
    code: str
    description: str
    domain: VersionedReleaseDomain = VersionedReleaseDomain.MAINTAINER_DECISION
    required: bool = True
    evidence: str = ""
    decision_required: bool = True


class PostReleaseChecklistItem(BaseModel):
    code: str
    description: str
    owner: str = "maintainer"
    safe_read_only: bool = True
    requires_authorization: bool = True


class ReleaseEvidenceMatrixItem(BaseModel):
    domain: VersionedReleaseDomain
    gate_status: VersionedReleaseGateStatus
    evidence: str
    included_scope: str
    limitation: str
    next_step: str


class VersionedReleaseHandoffReport(BaseModel):
    status: VersionedReleaseHandoffStatus
    decision: VersionedReleaseHandoffDecision
    target_version: str
    dependencies: dict[str, bool] = Field(default_factory=dict)
    domain_summaries: list[VersionedReleaseDomainSummary] = Field(default_factory=list)
    gates: list[VersionedReleaseGate] = Field(default_factory=list)
    release_notes: list[ReleaseNoteItem] = Field(default_factory=list)
    included_scope: list[ReleaseScopeItem] = Field(default_factory=list)
    known_limitations: list[KnownLimitationItem] = Field(default_factory=list)
    maintainer_decision_checklist: list[MaintainerDecisionChecklistItem] = Field(
        default_factory=list
    )
    post_release_checklist: list[PostReleaseChecklistItem] = Field(default_factory=list)
    release_evidence_matrix: list[ReleaseEvidenceMatrixItem] = Field(default_factory=list)
    domains_total: int
    domains_passed: int
    domains_needing_review: int
    domains_blocked: int
    gates_total: int
    gates_passed: int
    gates_needing_review: int
    findings: list[VersionedReleaseFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    release_notes_items_total: int = 0
    included_scope_items_total: int = 0
    known_limitations_total: int = 0
    maintainer_decision_items_total: int = 0
    post_release_items_total: int = 0
    public_repo_safe_for_release_handoff: bool = True
    maintainer_authorization_required: bool = True
    private_review_required: bool = True
    actual_release_performed: bool = False
    package_build_attempted: bool = False
    docker_build_attempted: bool = False
    publish_attempted: bool = False
    tag_attempted: bool = False
    release_attempted: bool = False
    deploy_attempted: bool = False
    docs_deploy_attempted: bool = False
    workflow_changed: bool = False
    github_api_attempted: bool = False
    package_registry_call_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_external_connection_attempted: bool = False
    scanner_attempted: bool = False
    production_approval_granted: bool = False
    release_approval_granted: bool = False
    pilot_approval_granted: bool = False
    deployment_approval_granted: bool = False
    package_publication_claimed: bool = False
    docs_hosting_claimed: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)

    @property
    def release_notes_draft(self) -> list[ReleaseNoteItem]:
        """Compatibility view used by callers that name the draft explicitly."""

        return self.release_notes

    @property
    def release_scope_summary(self) -> list[ReleaseScopeItem]:
        return self.included_scope

    @property
    def known_limitations_summary(self) -> list[KnownLimitationItem]:
        return self.known_limitations

    @property
    def maintainer_release_decision_checklist(self) -> list[MaintainerDecisionChecklistItem]:
        return self.maintainer_decision_checklist

    @property
    def release_notes_items(self) -> list[ReleaseNoteItem]:
        return self.release_notes

    @property
    def included_scope_items(self) -> list[ReleaseScopeItem]:
        return self.included_scope

    @property
    def known_limitation_items(self) -> list[KnownLimitationItem]:
        return self.known_limitations

    @property
    def maintainer_decision_items(self) -> list[MaintainerDecisionChecklistItem]:
        return self.maintainer_decision_checklist

    @property
    def post_release_items(self) -> list[PostReleaseChecklistItem]:
        return self.post_release_checklist

    @property
    def evidence_matrix(self) -> list[ReleaseEvidenceMatrixItem]:
        return self.release_evidence_matrix


class VersionedReleaseArtifactResult(BaseModel):
    status: VersionedReleaseHandoffStatus
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
