from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PermissionChecklistItem(BaseModel):
    category: Literal["required", "optional", "not_requested"]
    tool: str
    access: str
    rationale: str


class OnboardingPacketSection(BaseModel):
    key: str
    title: str
    content: list[str]


class TroubleshootingChecklistItem(BaseModel):
    symptom: str
    checks: list[str]


class OnboardingPacketCreate(BaseModel):
    packet_name: str = Field(default="GC Owner Onboarding Packet", min_length=1, max_length=200)
    recipient_company_name: str = Field(min_length=1, max_length=200)
    recipient_contact_name: str | None = Field(default=None, max_length=200)
    requester_company_name: str | None = Field(default=None, max_length=200)
    requester_contact_name: str | None = Field(default=None, max_length=200)
    app_name: str | None = Field(default=None, max_length=200)
    app_version_key_ref: str | None = Field(default=None, max_length=255)
    requested_project_ids: list[str] = Field(default_factory=list)
    requested_tools: list[Literal["rfis", "submittals"]] = Field(
        default_factory=lambda: ["rfis", "submittals"]
    )
    support_contact: str = Field(default="SUPPORT_CONTACT_PLACEHOLDER", max_length=200)
    connection_id: int | None = None
    sync_profile_id: int | None = None


class OnboardingPacketPreviewRequest(OnboardingPacketCreate):
    pass


class OnboardingPacketGenerateRequest(OnboardingPacketCreate):
    pass


class OnboardingPacketPreviewResponse(BaseModel):
    markdown: str
    json_packet: dict
    sections: list[OnboardingPacketSection]
    permissions: list[PermissionChecklistItem]
    persisted: bool = False


class OnboardingPacketGenerateResponse(OnboardingPacketPreviewResponse):
    packet_id: int
    persisted: bool = True


class OnboardingPacketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    connection_id: int | None
    sync_profile_id: int | None
    packet_name: str
    packet_type: str
    recipient_company_name: str
    recipient_contact_name: str | None
    requester_company_name: str
    requester_contact_name: str | None
    app_name: str
    app_version_key_ref: str | None
    requested_project_ids_json: list[str]
    requested_tools_json: list[str]
    requested_permissions_json: list[dict]
    safety_summary_json: list[str]
    generated_markdown: str
    generated_json: dict
    status: Literal["draft", "generated", "archived"]
    created_at: datetime
    updated_at: datetime


class OnboardingPacketExportResponse(BaseModel):
    packet_id: int
    markdown_path: str
    json_path: str
    message: str
