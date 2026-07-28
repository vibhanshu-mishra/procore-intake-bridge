from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    procore_company_id: str = Field(min_length=1, max_length=100)
    environment: Literal["sandbox", "production"] = "sandbox"
    permitted_project_ids: list[str] = Field(min_length=1)
    enabled_tools: list[Literal["rfis", "submittals"]] = ["rfis", "submittals"]
    secret_name: str = Field(
        min_length=1,
        description="Reference to a secret manager entry; never a plaintext client secret.",
    )


class ConnectionRead(ConnectionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auth_mode: Literal["dmsa_client_credentials"]
    status: Literal["pending", "active", "degraded", "revoked"]
    created_at: datetime
    updated_at: datetime
