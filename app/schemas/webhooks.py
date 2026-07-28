from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WebhookEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    resource_type: str
    action: str
    processing_status: str
    signature_status: str
    received_at: datetime
    processed_at: datetime | None
    failure_count: int


class WebhookEventRead(WebhookEventListItem):
    connection_id: int | None
    sync_profile_id: int | None
    source: str
    procore_company_id: str | None
    procore_project_id: str | None
    procore_item_id: str | None
    normalized_json: dict[str, Any]
    available_at: datetime
    last_error_code: str | None
    last_error_message: str | None
    locked_at: datetime | None
    lock_owner: str | None
    created_at: datetime
    updated_at: datetime


class WebhookReceiveResult(BaseModel):
    accepted: bool
    persisted: bool
    duplicate: bool
    webhook_event_id: int | None
    event_id: str
    resource_type: str
    action: str
    signature_status: str
    processing_status: str
    message: str


class WebhookDryRunRequest(BaseModel):
    payload: dict[str, Any]


class EventProcessingResult(BaseModel):
    webhook_event_id: int
    status: Literal["processed", "skipped", "failed", "dry_run"]
    sync_profile_id: int | None = None
    sync_status: str | None = None
    record_count: int = 0
    error_code: str | None = None
    message: str


class EventQueueRunResult(BaseModel):
    queued_count: int
    attempted_count: int
    processed_count: int
    skipped_count: int
    failed_count: int
    dry_run: bool
    results: list[EventProcessingResult]


class EventQueueOptions(BaseModel):
    dry_run: bool = True
    limit: int = Field(default=25, ge=1, le=100)
    force: bool = False
