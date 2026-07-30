from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictHostedDeploymentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HostedDeploymentPlatform(StrEnum):
    DOCKER_VPS = "docker_vps"
    MANAGED_PAAS = "managed_paas"
    RENDER_STYLE = "render_style"
    RAILWAY_STYLE = "railway_style"
    FLY_STYLE = "fly_style"
    GENERIC_CONTAINER_HOST = "generic_container_host"
    AWS_ECS_STYLE = "aws_ecs_style"
    AZURE_CONTAINER_APPS_STYLE = "azure_container_apps_style"
    GCP_CLOUD_RUN_STYLE = "gcp_cloud_run_style"


class HostedDeploymentStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"


class HostedDeploymentFinding(StrictHostedDeploymentModel):
    code: str
    severity: str = "blocking"
    message: str


class HostedDeploymentRequirement(StrictHostedDeploymentModel):
    name: str
    status: HostedDeploymentStatus
    message: str


class HostedDeploymentTemplateProfile(StrictHostedDeploymentModel):
    profile_name: str
    platform: HostedDeploymentPlatform
    environment_label: str = "ENVIRONMENT_LABEL_PLACEHOLDER"
    container_image_placeholder: str = "CONTAINER_IMAGE_PLACEHOLDER"
    registry_ref_placeholder: str = "REGISTRY_REF_PLACEHOLDER"
    public_url_placeholder: str = "PUBLIC_URL_PLACEHOLDER"
    allowed_hosts_placeholder: str = "ALLOWED_HOSTS_PLACEHOLDER"
    database_url_ref_placeholder: str = "DATABASE_URL_REF_PLACEHOLDER"
    admin_token_ref_placeholder: str = "ADMIN_TOKEN_REF_PLACEHOLDER"
    dmsa_client_id_ref_placeholder: str = "DMSA_CLIENT_ID_REF_PLACEHOLDER"
    dmsa_client_secret_ref_placeholder: str = "DMSA_CLIENT_SECRET_REF_PLACEHOLDER"
    webhook_secret_ref_placeholder: str = "WEBHOOK_SECRET_REF_PLACEHOLDER"
    secret_provider_placeholder: str = "SECRET_PROVIDER_REF_PLACEHOLDER"
    storage_provider_placeholder: str = "STORAGE_PROVIDER_REF_PLACEHOLDER"
    postgres_runtime_placeholder: str = "POSTGRES_RUNTIME_REF_PLACEHOLDER"
    migration_plan_placeholder: str = "MIGRATION_PLAN_REF_PLACEHOLDER"
    backup_plan_placeholder: str = "BACKUP_PLAN_REF_PLACEHOLDER"
    rollback_plan_placeholder: str = "ROLLBACK_PLAN_REF_PLACEHOLDER"
    tls_https_placeholder: str = "TLS_HTTPS_REF_PLACEHOLDER"
    webhook_ingress_placeholder: str = "WEBHOOK_INGRESS_REF_PLACEHOLDER"
    health_check_placeholder: str = "HEALTH_CHECK_REF_PLACEHOLDER"
    scaling_placeholder: str = "SCALING_PLAN_REF_PLACEHOLDER"
    logging_placeholder: str = "LOGGING_PLAN_REF_PLACEHOLDER"
    monitoring_placeholder: str = "MONITORING_PLAN_REF_PLACEHOLDER"
    known_limitations: list[str] = Field(
        default_factory=lambda: ["KNOWN_LIMITATION_PLACEHOLDER"]
    )
    notes: list[str] = Field(
        default_factory=lambda: ["PRIVATE_ADAPTATION_REQUIRED_PLACEHOLDER"]
    )


class HostedDeploymentTemplateReport(StrictHostedDeploymentModel):
    profile_name: str
    platform: HostedDeploymentPlatform
    status: HostedDeploymentStatus
    requirements: list[HostedDeploymentRequirement]
    findings: list[HostedDeploymentFinding]
    placeholder_only: bool
    external_calls: bool = False
    deployment_executed: bool = False
    cloud_resources_created: bool = False
    registry_accessed: bool = False
    images_pushed: bool = False
    dns_changes_made: bool = False
    certificates_issued: bool = False
    private_values_exposed: bool = False
    infrastructure_ids_exposed: bool = False
    cloud_ids_exposed: bool = False
    registry_refs_exposed: bool = False
    domains_exposed: bool = False
    local_paths_exposed: bool = False


class HostedDeploymentArtifactResult(StrictHostedDeploymentModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    deployment_executed: bool = False
    private_values_exposed: bool = False
