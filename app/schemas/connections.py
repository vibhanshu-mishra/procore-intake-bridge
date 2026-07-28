from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.config import get_settings
from app.security.secret_refs import mask_secret_ref


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    procore_company_id: str = Field(min_length=1, max_length=100)
    environment: Literal["sandbox", "production"] = "sandbox"
    permitted_project_ids: list[str] = Field(min_length=1)
    enabled_tools: list[Literal["rfis", "submittals"]] = ["rfis", "submittals"]
    client_id_ref: str | None = Field(
        default=None,
        min_length=1,
        description="Optional environment-secret reference for the DMSA client ID.",
    )
    secret_name: str = Field(
        min_length=1,
        description="Reference to a secret manager entry; never a plaintext client secret.",
    )


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    procore_company_id: str
    environment: Literal["sandbox", "production"]
    auth_mode: Literal["dmsa_client_credentials"]
    permitted_project_ids: list[str]
    enabled_tools: list[Literal["rfis", "submittals"]]
    client_id_ref: str | None
    secret_name: str
    status: Literal["pending", "active", "degraded", "revoked"]
    created_at: datetime
    updated_at: datetime

    @field_serializer("client_id_ref", "secret_name")
    def serialize_secret_ref(self, value: str | None) -> str | None:
        return mask_secret_ref(value, get_settings()) if value else None
