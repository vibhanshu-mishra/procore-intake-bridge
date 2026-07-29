from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictDeploymentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeploymentTargetKind(StrEnum):
    DOCKER_LOCAL = "docker_local"
    DOCKER_VPS = "docker_vps"
    MANAGED_PAAS = "managed_paas"
    GENERIC_CLOUD = "generic_cloud"


class DeploymentRecipeStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class DeploymentFinding(StrictDeploymentModel):
    code: str
    severity: str
    message: str


class DeploymentRequirement(StrictDeploymentModel):
    requirement: str
    status: DeploymentRecipeStatus
    message: str


class DeploymentRecipeProfile(StrictDeploymentModel):
    recipe_name: str
    target_kind: DeploymentTargetKind
    environment_label: str = "EXAMPLE_ENVIRONMENT_PLACEHOLDER"
    public_base_url_placeholder: str = "PUBLIC_BASE_URL_PLACEHOLDER"
    allowed_hosts_placeholders: list[str] = Field(
        default_factory=lambda: ["ALLOWED_HOST_PLACEHOLDER"]
    )
    database_url_ref_placeholder: str = "DATABASE_URL_REF_PLACEHOLDER"
    secret_provider_ref_placeholder: str = "SECRET_PROVIDER_REF_PLACEHOLDER"
    storage_provider_ref_placeholder: str = "STORAGE_PROVIDER_REF_PLACEHOLDER"
    admin_auth_ref_placeholder: str = "ADMIN_AUTH_REF_PLACEHOLDER"
    webhook_secret_ref_placeholder: str = "WEBHOOK_SECRET_REF_PLACEHOLDER"
    tls_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_CONFIGURATION
    public_ingress_status: DeploymentRecipeStatus = (
        DeploymentRecipeStatus.NEEDS_CONFIGURATION
    )
    database_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_CONFIGURATION
    migration_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_REVIEW
    backup_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_REVIEW
    rollback_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_REVIEW
    diagnostics_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_REVIEW
    operator_runbook_status: DeploymentRecipeStatus = DeploymentRecipeStatus.NEEDS_REVIEW
    webhooks_planned: bool = False
    known_limitations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DeploymentEnvironmentRef(StrictDeploymentModel):
    environment_label: str
    public_base_url_placeholder: str
    allowed_hosts_placeholders: list[str]


class DeploymentHttpsPlan(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    certificate_ref_placeholder: str = "TLS_CERT_REF_PLACEHOLDER"
    external_calls: bool = False


class DeploymentWebhookIngressPlan(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    ingress_ref_placeholder: str = "WEBHOOK_INGRESS_REF_PLACEHOLDER"
    external_calls: bool = False


class DeploymentBackupPlanSummary(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    plan_ref_placeholder: str = "BACKUP_PLAN_REF_PLACEHOLDER"


class DeploymentRollbackPlanSummary(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    plan_ref_placeholder: str = "ROLLBACK_PLAN_REF_PLACEHOLDER"


class DeploymentCutoverPlan(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    steps: list[str]
    deployment_executed: bool = False


class DeploymentOperatorRunbookSummary(StrictDeploymentModel):
    status: DeploymentRecipeStatus
    runbook_ref_placeholder: str = "OPERATOR_RUNBOOK_REF_PLACEHOLDER"


class DeploymentRecipeReadinessReport(StrictDeploymentModel):
    recipe_name: str
    target_kind: DeploymentTargetKind
    status: DeploymentRecipeStatus
    requirements: list[DeploymentRequirement]
    findings: list[DeploymentFinding]
    external_calls: bool = False
    deployment_executed: bool = False
    dns_changes_made: bool = False
    certificates_issued: bool = False
    webhooks_registered: bool = False
    values_exposed: bool = False
    domains_exposed: bool = False
    certificate_contents_exposed: bool = False
    infrastructure_ids_exposed: bool = False
    local_paths_exposed: bool = False


class DeploymentRecipeArtifactResult(StrictDeploymentModel):
    recipe_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    deployment_executed: bool = False
    values_exposed: bool = False
    local_paths_exposed: bool = False
