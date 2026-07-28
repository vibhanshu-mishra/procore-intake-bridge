from datetime import datetime

from pydantic import BaseModel, Field


class AdminCountCard(BaseModel):
    label: str
    count: int
    breakdown: dict[str, int] = Field(default_factory=dict)
    empty_message: str | None = None


class AdminRecentConnection(BaseModel):
    id: int
    display_name: str
    company_id_masked: str
    environment: str
    status: str
    project_count: int
    created_at: datetime


class AdminRecentSyncProfile(BaseModel):
    id: int
    connection_id: int
    display_name: str
    project_id_masked: str
    enabled: bool
    mode: str
    next_run_at: datetime | None
    consecutive_failure_count: int


class AdminRecentSyncRun(BaseModel):
    id: int
    connection_id: int
    mode: str
    status: str
    record_count: int
    attachment_count: int
    started_at: datetime
    completed_at: datetime | None


class AdminRecentIntakeRecord(BaseModel):
    id: int
    source_type: str
    project_id_masked: str
    item_id_masked: str
    number_masked: str
    status: str
    attachment_count: int
    updated_at: datetime


class AdminRecentAttachment(BaseModel):
    id: int
    intake_record_id: int | None
    source_type: str
    project_id_masked: str | None
    filename_display: str
    content_type: str | None
    size_bytes: int | None
    download_status: str
    checksum_present: bool


class AdminRecentWebhookEvent(BaseModel):
    id: int
    event_id_masked: str
    event_type: str
    resource_type: str
    action: str
    processing_status: str
    failure_count: int
    received_at: datetime


class AdminRecentOnboardingPacket(BaseModel):
    id: int
    display_name: str
    connection_id: int | None
    status: str
    project_count: int
    created_at: datetime


class AdminSafetyStatus(BaseModel):
    live_mode_enabled: bool
    webhook_signature_required: bool
    fixture_only_downloads: bool
    admin_dashboard_enabled: bool
    admin_token_required: bool
    admin_auth_mode: str
    admin_token_header_name: str
    admin_primary_ref_configured: bool
    admin_rotation_ref_configured: bool
    admin_provider_health_status: str
    deployment_routes_protected: bool
    read_only: bool = True
    procore_writes: bool = False
    production_auth_warning: str


class AdminOverview(BaseModel):
    system_readiness: str
    count_cards: list[AdminCountCard]
    safety: AdminSafetyStatus
    recent_connections: list[AdminRecentConnection]
    recent_sync_profiles: list[AdminRecentSyncProfile]
    recent_sync_runs: list[AdminRecentSyncRun]
    recent_intake_records: list[AdminRecentIntakeRecord]
    recent_attachments: list[AdminRecentAttachment]
    recent_webhook_events: list[AdminRecentWebhookEvent]
    recent_onboarding_packets: list[AdminRecentOnboardingPacket]
