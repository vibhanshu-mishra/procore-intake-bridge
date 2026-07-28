from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SyncProfileCreate(BaseModel):
    connection_id: int
    procore_project_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    sync_rfis: bool = True
    sync_submittals: bool = True
    polling_interval_minutes: int | None = Field(default=None, gt=0)
    mode: Literal["mock", "live"] = "mock"

    @model_validator(mode="after")
    def require_source(self):
        if not self.sync_rfis and not self.sync_submittals:
            raise ValueError("At least one source must be enabled.")
        return self


class SyncProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    sync_rfis: bool | None = None
    sync_submittals: bool | None = None
    polling_interval_minutes: int | None = Field(default=None, gt=0)
    mode: Literal["mock", "live"] | None = None


class SyncProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    connection_id: int
    procore_project_id: str
    name: str
    enabled: bool
    sync_rfis: bool
    sync_submittals: bool
    polling_interval_minutes: int
    mode: Literal["mock", "live"]
    last_successful_sync_at: datetime | None
    last_attempted_sync_at: datetime | None
    next_run_at: datetime | None
    last_watermark_at: datetime | None
    consecutive_failure_count: int
    last_error_code: str | None
    last_error_message: str | None
    locked_at: datetime | None
    lock_owner: str | None
    created_at: datetime
    updated_at: datetime


class SyncProfileState(BaseModel):
    id: int
    enabled: bool
    mode: str
    due: bool
    locked: bool
    last_successful_sync_at: datetime | None
    last_attempted_sync_at: datetime | None
    next_run_at: datetime | None
    last_watermark_at: datetime | None
    consecutive_failure_count: int
    last_error_code: str | None
    last_error_message: str | None


class SyncProfileRunResult(BaseModel):
    sync_profile_id: int
    status: Literal["succeeded", "failed", "skipped", "dry_run"]
    mode: Literal["mock", "live"]
    dry_run: bool
    planned_updated_after: datetime
    watermark_advanced_to: datetime | None = None
    record_count: int = 0
    attachment_count: int = 0
    sync_run_id: int | None = None
    error_code: str | None = None
    message: str


class PollingRunSummary(BaseModel):
    due_profiles_count: int
    attempted_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    dry_run: bool
    results: list[SyncProfileRunResult]
