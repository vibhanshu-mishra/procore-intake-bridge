"""Public-safe models for the offline J10 post-release roadmap.

The roadmap is a maintainer review aid.  It describes work that may happen
after a future, separately authorised 0.1.0 release; it never represents a
release, deployment, approval, or live operation.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class PostReleaseRoadmapStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class PostReleaseRoadmapDecision(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "post_release_roadmap_ready_for_maintainer_review"
    NEEDS_REVIEW = "post_release_roadmap_needs_review"
    BLOCKED = "post_release_roadmap_blocked"
    NOT_RUN = "post_release_roadmap_not_run"


class RoadmapDomain(StrEnum):
    PRIVATE_REVIEW = "private_review"
    HOSTED_PILOT = "hosted_pilot"
    PRODUCTIONIZATION = "productionization"
    LIVE_SANDBOX_VALIDATION = "live_sandbox_validation"
    CUSTOMER_ONBOARDING = "customer_onboarding"
    NOTIFICATIONS_ALERTING = "notifications_alerting"
    AUDIT_LOGGING = "audit_logging"
    DATA_RETENTION = "data_retention"
    ENCRYPTION_AT_REST = "encryption_at_rest"
    PRIVACY_LEGAL = "privacy_legal"
    SECURITY_COMPLIANCE = "security_compliance"
    API_HARDENING = "api_hardening"
    HOSTED_UI = "hosted_ui"
    OPERATOR_EXPERIENCE = "operator_experience"
    DOCS_HOSTING = "docs_hosting"
    RELEASE_AUTOMATION = "release_automation"
    OBSERVABILITY = "observability"
    SUPPORT_OPERATIONS = "support_operations"
    PRODUCT_BACKLOG = "product_backlog"
    KNOWN_LIMITATIONS = "known_limitations"
    PRE_TAG_DECISION = "pre_tag_decision"


class RoadmapItemStatus(StrEnum):
    NOT_STARTED = "not_started"
    PLANNED = "planned"
    REQUIRES_PRIVATE_REVIEW = "requires_private_review"
    FUTURE_WORK = "future_work"
    INTENTIONALLY_OUT_OF_SCOPE_FOR_0_1_0 = "intentionally_out_of_scope_for_0_1_0"
    BLOCKED_UNTIL_MAINTAINER_DECISION = "blocked_until_maintainer_decision"
    BLOCKED_UNTIL_PRIVATE_REVIEW = "blocked_until_private_review"


class RoadmapPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFERRED = "deferred"
    MAINTAINER_DECISION = "maintainer_decision"


class RoadmapTimeframe(StrEnum):
    BEFORE_MANUAL_RELEASE = "before_manual_release"
    AFTER_0_1_0_RELEASE = "after_0_1_0_release"
    BEFORE_PRIVATE_PILOT = "before_private_pilot"
    BEFORE_HOSTED_PILOT = "before_hosted_pilot"
    BEFORE_PRODUCTION_USE = "before_production_use"
    LATER = "later"
    NOT_SCHEDULED = "not_scheduled"


class KnownLimitationCategory(StrEnum):
    PRIVATE_REVIEW = "private_review"
    PRODUCTION_APPROVAL = "production_approval"
    HOSTED_DEPLOYMENT = "hosted_deployment"
    NOTIFICATIONS = "notifications"
    AUDIT_LOG = "audit_log"
    RETENTION = "retention"
    ENCRYPTION = "encryption"
    PRIVACY_LEGAL = "privacy_legal"
    API_HARDENING = "api_hardening"
    HOSTED_UI = "hosted_ui"
    RELEASE_AUTOMATION = "release_automation"
    DOCUMENTATION_HOSTING = "documentation_hosting"
    OBSERVABILITY = "observability"
    SUPPORT_OPERATIONS = "support_operations"
    # Readable aliases used by earlier roadmap drafts and downstream callers.
    NO_PRODUCTION_APPROVAL = "production_approval"
    NO_HOSTED_DEPLOYMENT = "hosted_deployment"
    NO_NOTIFICATION_SYSTEM = "notifications"
    NO_FULL_AUDIT_LOG = "audit_log"
    NO_RETENTION_ENFORCEMENT = "retention"
    NO_APP_LEVEL_ENCRYPTION = "encryption"
    NO_PRIVACY_LEGAL_COMPLIANCE = "privacy_legal"


class FutureWorkCategory(StrEnum):
    PRIVATE_REVIEW = "private_review"
    PRODUCTIONIZATION = "productionization"
    HOSTED_PILOT = "hosted_pilot"
    LIVE_SANDBOX_VALIDATION = "live_sandbox_validation"
    CUSTOMER_ONBOARDING = "customer_onboarding"
    NOTIFICATIONS_ALERTING = "notifications_alerting"
    AUDIT_LOGGING = "audit_logging"
    DATA_RETENTION = "data_retention"
    ENCRYPTION_AT_REST = "encryption_at_rest"
    PRIVACY_LEGAL = "privacy_legal"
    SECURITY_COMPLIANCE = "security_compliance"
    API_HARDENING = "api_hardening"
    HOSTED_UI = "hosted_ui"
    OPERATOR_PRODUCT = "operator_product"
    DOCUMENTATION_HOSTING = "documentation_hosting"
    RELEASE_AUTOMATION = "release_automation"
    OBSERVABILITY = "observability"
    SUPPORT_OPERATIONS = "support_operations"


class PostReleaseFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    domain: RoadmapDomain | None = None
    source: str | None = None


class RoadmapDomainSummary(BaseModel):
    domain: RoadmapDomain
    status: RoadmapItemStatus
    summary: str
    source: str = "local repository"
    public_safe: bool = True
    private_review_required: bool = False


class KnownLimitationItem(BaseModel):
    category: KnownLimitationCategory
    title: str
    summary: str
    next_step: str
    status: RoadmapItemStatus = RoadmapItemStatus.INTENTIONALLY_OUT_OF_SCOPE_FOR_0_1_0
    priority: RoadmapPriority = RoadmapPriority.HIGH
    timeframe: RoadmapTimeframe = RoadmapTimeframe.AFTER_0_1_0_RELEASE
    private_review_required: bool = True
    public_safe: bool = True


class FutureWorkItem(BaseModel):
    category: FutureWorkCategory
    domain: RoadmapDomain | None = None
    title: str
    summary: str
    next_step: str
    status: RoadmapItemStatus = RoadmapItemStatus.FUTURE_WORK
    priority: RoadmapPriority = RoadmapPriority.MEDIUM
    timeframe: RoadmapTimeframe = RoadmapTimeframe.AFTER_0_1_0_RELEASE
    private_review_required: bool = False
    public_safe: bool = True


class PrivateReviewBacklogItem(FutureWorkItem):
    category: FutureWorkCategory = FutureWorkCategory.PRIVATE_REVIEW
    status: RoadmapItemStatus = RoadmapItemStatus.BLOCKED_UNTIL_PRIVATE_REVIEW
    private_review_required: bool = True


class ProductionizationBacklogItem(FutureWorkItem):
    category: FutureWorkCategory = FutureWorkCategory.PRODUCTIONIZATION
    timeframe: RoadmapTimeframe = RoadmapTimeframe.BEFORE_PRODUCTION_USE
    private_review_required: bool = True


class HostedPilotBacklogItem(FutureWorkItem):
    category: FutureWorkCategory = FutureWorkCategory.HOSTED_PILOT
    timeframe: RoadmapTimeframe = RoadmapTimeframe.BEFORE_HOSTED_PILOT
    private_review_required: bool = True


class SecurityFutureWorkItem(FutureWorkItem):
    category: FutureWorkCategory = FutureWorkCategory.SECURITY_COMPLIANCE
    private_review_required: bool = True


class ProductImprovementItem(FutureWorkItem):
    category: FutureWorkCategory = FutureWorkCategory.OPERATOR_PRODUCT


class PreTagReminderItem(BaseModel):
    code: str
    description: str
    required: bool = True
    owner: str = "maintainer"
    decision_required: bool = True
    public_safe: bool = True


class PostReleaseRoadmapMatrixItem(BaseModel):
    domain: RoadmapDomain
    status: RoadmapItemStatus
    priority: RoadmapPriority
    timeframe: RoadmapTimeframe
    summary: str
    known_limitation: str
    next_step: str


class PostReleaseRoadmapReport(BaseModel):
    status: PostReleaseRoadmapStatus
    decision: PostReleaseRoadmapDecision
    target_version: str
    dependencies: dict[str, bool] = Field(default_factory=dict)
    domain_summaries: list[RoadmapDomainSummary] = Field(default_factory=list)
    roadmap_items: list[PostReleaseFinding] = Field(default_factory=list)
    known_limitations: list[KnownLimitationItem] = Field(default_factory=list)
    future_work_backlog: list[FutureWorkItem] = Field(default_factory=list)
    private_review_backlog: list[PrivateReviewBacklogItem] = Field(default_factory=list)
    productionization_backlog: list[ProductionizationBacklogItem] = Field(default_factory=list)
    hosted_pilot_backlog: list[HostedPilotBacklogItem] = Field(default_factory=list)
    security_future_work: list[SecurityFutureWorkItem] = Field(default_factory=list)
    product_improvement_backlog: list[ProductImprovementItem] = Field(default_factory=list)
    pre_tag_reminders: list[PreTagReminderItem] = Field(default_factory=list)
    roadmap_matrix: list[PostReleaseRoadmapMatrixItem] = Field(default_factory=list)
    findings: list[PostReleaseFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    roadmap_items_total: int = 0
    known_limitations_total: int = 0
    private_review_items_total: int = 0
    productionization_items_total: int = 0
    hosted_pilot_items_total: int = 0
    security_future_work_items_total: int = 0
    product_improvement_items_total: int = 0
    pre_tag_reminders_total: int = 0
    public_repo_safe_for_roadmap_review: bool = True
    maintainer_decision_required: bool = True
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
    issue_creation_attempted: bool = False
    ticket_creation_attempted: bool = False
    package_registry_call_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    notification_attempted: bool = False
    telemetry_added: bool = False
    production_approval_granted: bool = False
    release_approval_granted: bool = False
    pilot_approval_granted: bool = False
    deployment_approval_granted: bool = False
    compliance_claimed: bool = False
    certification_claimed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)

    @property
    def future_work(self) -> list[FutureWorkItem]:
        return self.future_work_backlog

    @property
    def security_future_work_register(self) -> list[SecurityFutureWorkItem]:
        return self.security_future_work

    @property
    def product_backlog(self) -> list[ProductImprovementItem]:
        return self.product_improvement_backlog


class PostReleaseRoadmapArtifactResult(BaseModel):
    status: PostReleaseRoadmapStatus
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
