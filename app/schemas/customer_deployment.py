from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CustomerDeploymentEnvironment(BaseModel):
    name: Literal["local", "staging", "production"]
    public_base_url: str = ""
    allowed_hosts: list[str] = Field(default_factory=list)


class CustomerDeploymentSecretRef(BaseModel):
    purpose: str
    reference: str
    required: bool = True


class CustomerDeploymentProjectScope(BaseModel):
    company_id: str
    project_id: str
    project_label: str


class CustomerDeploymentToolScope(BaseModel):
    rfis: bool = True
    submittals: bool = True
    attachments: bool = False


class CustomerDeploymentWebhookPlan(BaseModel):
    enabled: bool = False
    signature_required: bool = True
    secret_ref: str = ""
    docs_verification_status: Literal[
        "unverified", "needs_review", "verified", "deprecated"
    ] = "unverified"
    verification_report_ref: str = ""


class CustomerDeploymentStoragePlan(BaseModel):
    provider: Literal["local", "disabled", "test", "external_placeholder"] = "local"
    bucket_ref: str = ""
    backup_plan: str = ""
    rollback_plan: str = ""


class CustomerDeploymentAdminAuthPlan(BaseModel):
    mode: Literal["local_optional", "token_required", "disabled"] = "local_optional"
    token_ref: str = ""
    rotation_token_ref: str = ""


class CustomerDeploymentProfile(BaseModel):
    profile_name: str = Field(min_length=1, max_length=100)
    customer_label: str = Field(min_length=1, max_length=200)
    environment: Literal["local", "staging", "production"] = "local"
    public_base_url: str = ""
    allowed_hosts: list[str] = Field(default_factory=list)
    requested_project_scopes: list[CustomerDeploymentProjectScope] = Field(
        default_factory=list
    )
    requested_tools: CustomerDeploymentToolScope = Field(
        default_factory=CustomerDeploymentToolScope
    )
    dmsa_connection_ref: str = ""
    dmsa_client_id_ref: str = ""
    dmsa_client_secret_ref: str = ""
    admin_token_ref: str = ""
    admin_rotation_token_ref: str = ""
    admin_auth_plan: CustomerDeploymentAdminAuthPlan = Field(
        default_factory=CustomerDeploymentAdminAuthPlan
    )
    webhook_secret_ref: str = ""
    secret_provider: Literal[
        "env", "disabled", "test", "external_placeholder", "managed_reference"
    ] = "external_placeholder"
    storage_provider: Literal[
        "local", "disabled", "test", "external_placeholder", "managed_reference"
    ] = "external_placeholder"
    storage_bucket_ref: str = ""
    database_profile: str = "sqlite-local"
    migration_plan: str = ""
    backup_plan: str = ""
    rollback_plan: str = ""
    smoke_test_required: bool = True
    sandbox_smoke_result_ref: str = ""
    webhook_verification_required: bool = True
    webhook_plan: CustomerDeploymentWebhookPlan = Field(
        default_factory=CustomerDeploymentWebhookPlan
    )
    onboarding_packet_required: bool = True
    onboarding_packet_ref: str = ""
    deployment_owner_placeholder: str = "DEPLOYMENT_OWNER_PLACEHOLDER"
    support_contact_placeholder: str = "SUPPORT_CONTACT_PLACEHOLDER"
    notes: list[str] = Field(default_factory=list)


class CustomerDeploymentReadinessFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "blocking"]
    message: str


class CustomerDeploymentReadinessReport(BaseModel):
    profile_name: str
    environment: str
    ready: bool
    blocking_findings_count: int
    warning_findings_count: int
    findings: list[CustomerDeploymentReadinessFinding]
    generated_at: datetime
    local_planning_only: bool = True
    deployed: bool = False
    external_calls: bool = False


class CustomerDeploymentArtifactResult(BaseModel):
    profile_name: str
    output_directory: str
    files: list[str]
    secrets_included: bool = False
    external_calls: bool = False


class CustomerDeploymentChecklistSection(BaseModel):
    title: str
    items: list[str]
