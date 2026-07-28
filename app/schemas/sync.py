from pydantic import BaseModel, Field

from app.schemas.attachments import AttachmentPlanResult


class AttachmentManifestEntry(BaseModel):
    source_type: str
    procore_project_id: str
    procore_item_id: str
    procore_attachment_id: str
    filename: str
    content_type: str | None = None


class NormalizedRecord(BaseModel):
    source_type: str
    procore_project_id: str
    procore_item_id: str
    number: str
    title: str
    status: str
    due_date: str | None
    received_at: str | None
    updated_at: str | None
    attachment_count: int


class SyncSummary(BaseModel):
    dry_run: bool
    mode: str
    sync_run_id: int | None
    record_count: int
    attachment_count: int
    records: list[NormalizedRecord]
    attachment_manifest: list[AttachmentManifestEntry]
    attachment_plans: list[AttachmentPlanResult] = Field(default_factory=list)
