from enum import StrEnum

from pydantic import BaseModel, Field


class DemoDataStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class DemoDataDecision(StrEnum):
    READY = "demo_data_ready"
    NEEDS_REVIEW = "demo_data_needs_review"
    BLOCKED = "demo_data_blocked"
    NOT_RUN = "demo_data_not_run"


class DemoDatasetKind(StrEnum):
    INTAKE_RECORDS = "intake_records"
    ATTACHMENT_MANIFESTS = "attachment_manifests"
    LIFECYCLE_STATES = "lifecycle_states"
    LIFECYCLE_EVENTS = "lifecycle_events"
    TRIAGE_SIGNALS = "triage_signals"
    DASHBOARD_COUNTS = "dashboard_counts"
    EXPORT_SUMMARIES = "export_summaries"
    EVENT_QUEUE_FIXTURES = "event_queue_fixtures"
    SYNC_RUN_FIXTURES = "sync_run_fixtures"


class DemoSeedAction(StrEnum):
    CREATE = "create"
    REUSE = "reuse"
    VERIFY = "verify"


class DemoResetAction(StrEnum):
    REMOVE_DEMO_MARKED = "remove_demo_marked"
    PRESERVE_UNMARKED = "preserve_unmarked"
    REQUIRE_CONFIRMATION = "require_confirmation"


class DemoDataFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    dataset_kind: DemoDatasetKind | None = None


class DemoDataRecordPlan(BaseModel):
    dataset_kind: DemoDatasetKind
    record_count: int = Field(ge=0)
    seed_action: DemoSeedAction = DemoSeedAction.CREATE
    reset_action: DemoResetAction = DemoResetAction.REMOVE_DEMO_MARKED
    description: str
    demo_marker: str = "J2_DEMO_"


class DemoDataInventoryItem(BaseModel):
    dataset_kind: DemoDatasetKind
    marker: str = "J2_DEMO_"
    record_count: int = Field(ge=0)
    fake_only: bool = True
    local_only: bool = True
    reset_eligible: bool = True
    description: str = "Deterministic local Demo Mode fixture records."


class DemoSeedReport(BaseModel):
    status: DemoDataStatus
    planned_total: int = 0
    seeded_total: int = 0
    already_present_total: int = 0
    actions: list[DemoDataRecordPlan] = Field(default_factory=list)
    findings: list[DemoDataFinding] = Field(default_factory=list)
    demo_only: bool = True
    fake_only: bool = True
    local_sqlite_only: bool = True
    idempotent: bool = True


class DemoResetReport(BaseModel):
    status: DemoDataStatus
    planned_total: int = 0
    removed_total: int = 0
    actions: list[DemoDataRecordPlan] = Field(default_factory=list)
    findings: list[DemoDataFinding] = Field(default_factory=list)
    confirmation_required: bool = True
    demo_only: bool = True
    local_sqlite_only: bool = True
    unmarked_records_preserved: bool = True


class DemoDataExperienceReport(BaseModel):
    status: DemoDataStatus
    decision: DemoDataDecision
    fake_records_planned_total: int = 0
    fake_records_seeded_total: int = 0
    reset_items_planned_total: int = 0
    reset_items_removed_total: int = 0
    findings: list[DemoDataFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dataset_plan: list[DemoDataRecordPlan] = Field(default_factory=list)
    inventory: list[DemoDataInventoryItem] = Field(default_factory=list)
    demo_only: bool = True
    fake_only: bool = True
    local_sqlite_only: bool = True
    idempotent_seed: bool = True
    reset_confirmation_required: bool = True
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    external_db_connection_attempted: bool = False
    sandbox_data_touched: bool = False
    pilot_data_touched: bool = False
    hosted_data_touched: bool = False
    private_workspace_touched: bool = False
    customer_data_touched: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    urls_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    real_domains_exposed: bool = False
    production_approval_claimed: bool = False
    release_approval_claimed: bool = False
    pilot_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class DemoDataArtifactResult(BaseModel):
    status: DemoDataStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    demo_only: bool = True
    live_operations: bool = False
    external_operations: bool = False
