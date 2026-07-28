from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AttachmentObjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intake_record_id: int | None
    sync_run_id: int | None
    connection_id: int | None
    sync_profile_id: int | None
    source_type: str
    procore_project_id: str | None
    procore_item_id: str | None
    procore_attachment_id: str | None
    original_filename: str
    safe_filename: str
    content_type: str | None
    size_bytes: int | None
    source_url_present: bool
    source_url_hash: str | None
    storage_backend: str
    storage_key: str
    storage_path: str
    checksum_sha256: str | None
    download_status: str
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class AttachmentPlanRequest(BaseModel):
    intake_record_id: int | None = None
    sync_run_id: int | None = None
    connection_id: int | None = None
    sync_profile_id: int | None = None
    source_type: Literal["rfi", "submittal", "unknown"] = "unknown"
    procore_project_id: str | None = None
    procore_item_id: str | None = None
    procore_attachment_id: str | None = None
    original_filename: str = Field(min_length=1, max_length=500)
    content_type: str | None = Field(default=None, max_length=200)
    size_bytes: int | None = Field(default=None, ge=0)
    source_url: str | None = Field(default=None, max_length=4000, exclude=True)


class AttachmentPlanResult(BaseModel):
    attachment_id: int | None
    persisted: bool
    safe_filename: str
    storage_backend: str
    storage_key: str
    storage_path: str
    source_url_present: bool
    source_url_hash: str | None
    download_status: str
    message: str


class AttachmentDownloadRequest(BaseModel):
    fixture_label: str = Field(default="deterministic-fixture", max_length=100)


class AttachmentDownloadResult(BaseModel):
    attachment_id: int
    safe_filename: str
    storage_key: str
    storage_path: str
    download_status: str
    size_bytes: int
    checksum_sha256: str
    message: str


class AttachmentManifestSummary(BaseModel):
    total: int
    planned: int
    downloaded: int
    skipped: int
    failed: int
