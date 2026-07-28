from pydantic import BaseModel


class ServiceHealth(BaseModel):
    status: str
    mode: str


class ConnectionHealthResult(BaseModel):
    token_check: str
    company_access: str
    project_access: dict[str, str]
    rfi_access: str
    submittal_access: str
    attachment_visibility: str
    webhook_status: str
    polling_status: str
    findings: list[str]
