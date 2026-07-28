from pydantic import BaseModel


class ServiceHealth(BaseModel):
    status: str
    mode: str


class ConnectionHealthResult(BaseModel):
    mode: str
    live_mode_enabled: bool
    secret_reference_present: bool
    secret_resolved: bool
    pyprocore_client_buildable: bool
    token_check: str
    company_access: str
    project_access: dict[str, str]
    rfi_access: str
    submittal_access: str
    attachment_visibility: str
    webhook_status: str
    polling_status: str
    findings: list[str]
