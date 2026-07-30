from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", extra="ignore", populate_by_name=True
    )

    environment: Literal["local", "staging", "production"] = Field(
        default="local",
        validation_alias=AliasChoices("PROCORE_INTAKE_ENVIRONMENT", "APP_DEPLOYMENT_ENVIRONMENT"),
    )
    require_safe_production_settings: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REQUIRE_SAFE_PRODUCTION_SETTINGS",
    )
    database_url: str = Field(
        default="sqlite:///./procore_intake_bridge.db",
        validation_alias=AliasChoices("PROCORE_INTAKE_DATABASE_URL", "APP_DATABASE_URL"),
    )
    public_base_url: str | None = Field(
        default=None, validation_alias="PROCORE_INTAKE_PUBLIC_BASE_URL"
    )
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        validation_alias="PROCORE_INTAKE_ALLOWED_HOSTS",
    )
    cors_origins: str = Field(default="", validation_alias="PROCORE_INTAKE_CORS_ORIGINS")
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        default="INFO", validation_alias="PROCORE_INTAKE_LOG_LEVEL"
    )
    enable_startup_checks: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_ENABLE_STARTUP_CHECKS"
    )
    fail_startup_on_unsafe_production: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FAIL_STARTUP_ON_UNSAFE_PRODUCTION",
    )
    migration_check_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MIGRATION_CHECK_ENABLED",
    )
    auto_run_migrations: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTO_RUN_MIGRATIONS",
    )
    fail_readiness_on_pending_migrations: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FAIL_READINESS_ON_PENDING_MIGRATIONS",
    )
    migration_script_location: Path = Field(
        default=Path("migrations"),
        validation_alias="PROCORE_INTAKE_MIGRATION_SCRIPT_LOCATION",
    )
    migration_allow_destructive: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_MIGRATION_ALLOW_DESTRUCTIVE",
    )
    procore_mode: Literal["fixture", "live"] = "fixture"
    fixture_dir: Path = Path("app/fixtures")
    procore_live_mode_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_LIVE_MODE_ENABLED", "APP_PROCORE_LIVE_MODE_ENABLED"
        ),
    )
    procore_api_base: str = Field(
        default="https://api.procore.com",
        validation_alias=AliasChoices("PROCORE_INTAKE_API_BASE", "APP_PROCORE_API_BASE"),
    )
    procore_login_url: str = Field(
        default="https://login.procore.com",
        validation_alias=AliasChoices("PROCORE_INTAKE_LOGIN_URL", "APP_PROCORE_LOGIN_URL"),
    )
    procore_request_timeout_seconds: int = Field(
        default=30,
        gt=0,
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_REQUEST_TIMEOUT_SECONDS",
            "APP_PROCORE_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    procore_environment: Literal["sandbox", "production"] = Field(
        default="production",
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_PROCORE_ENVIRONMENT", "APP_PROCORE_ENVIRONMENT"
        ),
    )
    secret_provider: Literal[
        "env",
        "file",
        "test",
        "disabled",
        "external_placeholder",
        "aws_secrets_manager",
        "azure_key_vault",
        "gcp_secret_manager",
    ] = Field(
        default="env",
        validation_alias=AliasChoices("PROCORE_INTAKE_SECRET_PROVIDER", "APP_SECRET_PROVIDER"),
    )
    secret_ref_prefix: str = Field(
        default="PROCORE_INTAKE_SECRET_",
        min_length=1,
        validation_alias="PROCORE_INTAKE_SECRET_REF_PREFIX",
    )
    secret_require_prefix: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_REQUIRE_PREFIX",
    )
    secret_mask_mode: Literal["last4"] = Field(
        default="last4",
        validation_alias="PROCORE_INTAKE_SECRET_MASK_MODE",
    )
    secret_health_check_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_HEALTH_CHECK_ENABLED",
    )
    secret_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_FAIL_CLOSED",
    )
    secret_provider_strict_redaction: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_STRICT_REDACTION",
    )
    secret_provider_allow_env: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_ALLOW_ENV",
    )
    secret_provider_allow_file: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_ALLOW_FILE",
    )
    secret_provider_allow_cloud: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_ALLOW_CLOUD",
    )
    secret_provider_cloud_network_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_CLOUD_NETWORK_ENABLED",
    )
    secret_provider_cloud_confirmation: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_CLOUD_CONFIRMATION",
    )
    secret_provider_cloud_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_CLOUD_TIMEOUT_SECONDS",
    )
    secret_provider_cloud_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_CLOUD_FAIL_CLOSED",
    )
    secret_provider_cloud_health_network_check: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_CLOUD_HEALTH_NETWORK_CHECK",
    )
    secret_provider_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECRET_PROVIDER_FAIL_CLOSED",
    )
    file_secret_root: Path = Field(
        default=Path("./private-workspace/environment/secrets"),
        validation_alias="PROCORE_INTAKE_FILE_SECRET_ROOT",
    )
    file_secret_allow_relative_refs: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FILE_SECRET_ALLOW_RELATIVE_REFS",
    )
    file_secret_max_bytes: int = Field(
        default=8192,
        ge=1,
        le=65536,
        validation_alias="PROCORE_INTAKE_FILE_SECRET_MAX_BYTES",
    )
    file_secret_require_private_root: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FILE_SECRET_REQUIRE_PRIVATE_ROOT",
    )
    aws_secrets_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AWS_SECRETS_ENABLED",
    )
    aws_region_ref: str = Field(
        default="AWS_REGION",
        validation_alias="PROCORE_INTAKE_AWS_REGION_REF",
    )
    aws_profile_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_AWS_PROFILE_REF",
    )
    aws_secret_id_prefix: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_AWS_SECRET_ID_PREFIX",
    )
    aws_require_region: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AWS_REQUIRE_REGION",
    )
    aws_allow_arns: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AWS_ALLOW_ARNS",
    )
    azure_key_vault_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AZURE_KEY_VAULT_ENABLED",
    )
    azure_key_vault_name_ref: str = Field(
        default="AZURE_KEY_VAULT_NAME",
        validation_alias="PROCORE_INTAKE_AZURE_KEY_VAULT_NAME_REF",
    )
    azure_key_vault_url_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_AZURE_KEY_VAULT_URL_REF",
    )
    azure_tenant_id_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_AZURE_TENANT_ID_REF",
    )
    azure_use_default_credential: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AZURE_USE_DEFAULT_CREDENTIAL",
    )
    azure_allow_vault_url: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AZURE_ALLOW_VAULT_URL",
    )
    gcp_secret_manager_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_GCP_SECRET_MANAGER_ENABLED",
    )
    gcp_project_id_ref: str = Field(
        default="GCP_PROJECT_ID",
        validation_alias="PROCORE_INTAKE_GCP_PROJECT_ID_REF",
    )
    gcp_secret_prefix: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_GCP_SECRET_PREFIX",
    )
    gcp_allow_resource_names: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_GCP_ALLOW_RESOURCE_NAMES",
    )
    external_secret_provider_name: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_EXTERNAL_SECRET_PROVIDER_NAME",
    )
    external_secret_provider_region: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_EXTERNAL_SECRET_PROVIDER_REGION",
    )
    external_secret_provider_project: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_EXTERNAL_SECRET_PROVIDER_PROJECT",
    )
    external_secret_provider_vault_url: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_EXTERNAL_SECRET_PROVIDER_VAULT_URL",
    )
    default_polling_interval_minutes: int = Field(
        default=30,
        gt=0,
        validation_alias="PROCORE_INTAKE_DEFAULT_POLLING_INTERVAL_MINUTES",
    )
    sync_lock_timeout_minutes: int = Field(
        default=30,
        gt=0,
        validation_alias="PROCORE_INTAKE_SYNC_LOCK_TIMEOUT_MINUTES",
    )
    worker_id: str = Field(
        default="local-dev-worker",
        min_length=1,
        validation_alias="PROCORE_INTAKE_WORKER_ID",
    )
    max_sync_lookback_days: int = Field(
        default=30,
        gt=0,
        validation_alias="PROCORE_INTAKE_MAX_SYNC_LOOKBACK_DAYS",
    )
    webhooks_enabled: bool = Field(default=True, validation_alias="PROCORE_INTAKE_WEBHOOKS_ENABLED")
    require_webhook_signature: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_REQUIRE_WEBHOOK_SIGNATURE",
    )
    webhook_signature_header: str = Field(
        default="x-procore-signature",
        min_length=1,
        validation_alias="PROCORE_INTAKE_WEBHOOK_SIGNATURE_HEADER",
    )
    webhook_event_id_header: str = Field(
        default="x-procore-event-id",
        min_length=1,
        validation_alias="PROCORE_INTAKE_WEBHOOK_EVENT_ID_HEADER",
    )
    webhook_secret_provider: str = Field(
        default="env",
        validation_alias="PROCORE_INTAKE_WEBHOOK_SECRET_PROVIDER",
    )
    webhook_secret_name: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_WEBHOOK_SECRET_NAME",
    )
    webhook_verification_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_ENABLED",
    )
    webhook_verification_require_confirmation: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_REQUIRE_CONFIRMATION",
    )
    webhook_verification_confirmation_phrase: str = Field(
        default="I_UNDERSTAND_THIS_ONLY_VERIFIES_WEBHOOK_RECEIVER_BEHAVIOR",
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_CONFIRMATION_PHRASE",
    )
    webhook_verification_allow_production: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_ALLOW_PRODUCTION",
    )
    webhook_verification_output_root: Path = Field(
        default=Path("./webhook-verification-output"),
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_OUTPUT_ROOT",
    )
    webhook_verification_write_report: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_WRITE_REPORT",
    )
    webhook_verification_max_events: int = Field(
        default=5,
        ge=1,
        le=10,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_MAX_EVENTS",
    )
    webhook_verification_require_docs_check: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_REQUIRE_DOCS_CHECK",
    )
    webhook_verification_docs_status: Literal[
        "unverified", "verified", "needs_review", "deprecated"
    ] = Field(
        default="unverified",
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_DOCS_STATUS",
    )
    webhook_verification_expected_payload_version: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_EXPECTED_PAYLOAD_VERSION",
    )
    webhook_verification_expected_scope: str = Field(
        default="company_or_project",
        validation_alias="PROCORE_INTAKE_WEBHOOK_VERIFICATION_EXPECTED_SCOPE",
    )
    event_lock_timeout_minutes: int = Field(
        default=30,
        gt=0,
        validation_alias="PROCORE_INTAKE_EVENT_LOCK_TIMEOUT_MINUTES",
    )
    event_max_attempts: int = Field(
        default=5,
        gt=0,
        validation_alias="PROCORE_INTAKE_EVENT_MAX_ATTEMPTS",
    )
    event_worker_id: str = Field(
        default="local-dev-event-worker",
        min_length=1,
        validation_alias="PROCORE_INTAKE_EVENT_WORKER_ID",
    )
    attachment_storage_provider: Literal["local", "test", "disabled", "external_placeholder"] = (
        Field(
            default="local",
            validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_PROVIDER",
        )
    )
    attachment_storage_backend: str = Field(
        default="local",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_BACKEND",
    )
    attachment_storage_root: Path = Field(
        default=Path("./storage/attachments"),
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_ROOT",
    )
    attachment_max_filename_length: int = Field(
        default=160,
        ge=32,
        le=255,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_MAX_FILENAME_LENGTH",
    )
    attachment_allow_overwrite: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_ALLOW_OVERWRITE",
    )
    attachment_fixture_downloads_only: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_FIXTURE_DOWNLOADS_ONLY",
    )
    attachment_storage_require_safe_keys: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_REQUIRE_SAFE_KEYS",
    )
    attachment_storage_health_check_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_HEALTH_CHECK_ENABLED",
    )
    attachment_storage_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_FAIL_CLOSED",
    )
    attachment_storage_max_object_bytes: int = Field(
        default=25_000_000,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_MAX_OBJECT_BYTES",
    )
    attachment_storage_allowed_content_types: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_ALLOWED_CONTENT_TYPES",
    )
    attachment_storage_quarantine_unknown_types: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_QUARANTINE_UNKNOWN_TYPES",
    )
    attachment_storage_write_metadata_only: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_WRITE_METADATA_ONLY",
    )
    attachment_storage_external_provider_name: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_EXTERNAL_PROVIDER_NAME",
    )
    attachment_storage_external_bucket_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_EXTERNAL_BUCKET_REF",
    )
    attachment_storage_external_region: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_EXTERNAL_REGION",
    )
    attachment_storage_external_endpoint_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_EXTERNAL_ENDPOINT_REF",
    )
    packet_output_root: Path = Field(
        default=Path("./packet-output"),
        validation_alias="PROCORE_INTAKE_PACKET_OUTPUT_ROOT",
    )
    default_requester_company_name: str = Field(
        default="Your Company",
        min_length=1,
        max_length=200,
        validation_alias="PROCORE_INTAKE_DEFAULT_REQUESTER_COMPANY_NAME",
    )
    default_app_name: str = Field(
        default="Procore Intake Bridge",
        min_length=1,
        max_length=200,
        validation_alias="PROCORE_INTAKE_DEFAULT_APP_NAME",
    )
    admin_dashboard_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ADMIN_DASHBOARD_ENABLED",
    )
    admin_auth_mode: Literal["local_optional", "token_required", "disabled"] = Field(
        default="local_optional",
        validation_alias="PROCORE_INTAKE_ADMIN_AUTH_MODE",
    )
    admin_token_header: str = Field(
        default="X-Procore-Intake-Admin-Token",
        min_length=1,
        validation_alias="PROCORE_INTAKE_ADMIN_TOKEN_HEADER",
    )
    admin_token_secret_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ADMIN_TOKEN_SECRET_REF",
    )
    admin_token_rotation_secret_ref: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ADMIN_TOKEN_ROTATION_SECRET_REF",
    )
    admin_auth_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ADMIN_AUTH_FAIL_CLOSED",
    )
    admin_auth_protect_deployment_routes: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ADMIN_AUTH_PROTECT_DEPLOYMENT_ROUTES",
    )
    admin_auth_cache_seconds: int = Field(
        default=0,
        ge=0,
        validation_alias="PROCORE_INTAKE_ADMIN_AUTH_CACHE_SECONDS",
    )
    admin_require_token: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ADMIN_REQUIRE_TOKEN",
    )
    admin_token_secret_name: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_ADMIN_TOKEN_SECRET_NAME",
    )
    admin_page_size: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_ADMIN_PAGE_SIZE",
    )
    product_dashboard_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_ENABLED"
    )
    product_dashboard_include_review_workspace: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_REVIEW_WORKSPACE"
    )
    product_dashboard_include_lifecycle: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_LIFECYCLE"
    )
    product_dashboard_include_triage: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_TRIAGE"
    )
    product_dashboard_include_attachments: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_ATTACHMENTS"
    )
    product_dashboard_include_exports: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_EXPORTS"
    )
    product_dashboard_include_sandbox_guidance: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_SANDBOX_GUIDANCE"
    )
    product_dashboard_include_pilot_guidance: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_INCLUDE_PILOT_GUIDANCE"
    )
    product_dashboard_mask_source_ids: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_MASK_SOURCE_IDS"
    )
    product_dashboard_hash_source_ids: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_HASH_SOURCE_IDS"
    )
    product_dashboard_expose_raw_payloads: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_EXPOSE_RAW_PAYLOADS"
    )
    product_dashboard_expose_private_paths: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_EXPOSE_PRIVATE_PATHS"
    )
    product_dashboard_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PRODUCT_DASHBOARD_FAIL_CLOSED"
    )
    demo_walkthrough_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ENABLED"
    )
    demo_walkthrough_output_root: Path = Field(
        default=Path("./demo-walkthrough-output"),
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_OUTPUT_ROOT",
    )
    demo_walkthrough_require_fake_data: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_REQUIRE_FAKE_DATA",
    )
    demo_walkthrough_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ALLOW_REAL_IDENTITIES",
    )
    demo_walkthrough_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ALLOW_REAL_DOMAINS",
    )
    demo_walkthrough_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ALLOW_REAL_URLS",
    )
    demo_walkthrough_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ALLOW_REPORT_CONTENTS",
    )
    demo_walkthrough_allow_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_ALLOW_PRIVATE_PATHS",
    )
    demo_walkthrough_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DEMO_WALKTHROUGH_FAIL_CLOSED"
    )
    security_threat_model_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ENABLED"
    )
    security_threat_model_output_root: Path = Field(
        default=Path("./security-threat-model-output"),
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_OUTPUT_ROOT",
    )
    security_threat_model_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_REQUIRE_PLACEHOLDERS",
    )
    security_threat_model_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ALLOW_REAL_IDENTITIES",
    )
    security_threat_model_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ALLOW_REAL_DOMAINS",
    )
    security_threat_model_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ALLOW_REAL_URLS",
    )
    security_threat_model_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ALLOW_REPORT_CONTENTS",
    )
    security_threat_model_allow_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_ALLOW_PRIVATE_PATHS",
    )
    security_threat_model_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_FAIL_CLOSED"
    )
    security_threat_model_max_findings: int = Field(
        default=300,
        ge=1,
        le=1000,
        validation_alias="PROCORE_INTAKE_SECURITY_THREAT_MODEL_MAX_FINDINGS",
    )
    auth_boundary_audit_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ENABLED"
    )
    auth_boundary_audit_output_root: Path = Field(
        default=Path("./auth-boundary-audit-output"),
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_OUTPUT_ROOT",
    )
    auth_boundary_audit_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_REQUIRE_PLACEHOLDERS",
    )
    auth_boundary_audit_require_admin_protection: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_REQUIRE_ADMIN_PROTECTION",
    )
    auth_boundary_audit_allow_public_health_routes: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_PUBLIC_HEALTH_ROUTES",
    )
    auth_boundary_audit_allow_lifecycle_post_only: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_LIFECYCLE_POST_ONLY",
    )
    auth_boundary_audit_require_webhook_signature: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_REQUIRE_WEBHOOK_SIGNATURE",
    )
    auth_boundary_audit_require_live_command_gates: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_REQUIRE_LIVE_COMMAND_GATES",
    )
    auth_boundary_audit_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_REAL_IDENTITIES",
    )
    auth_boundary_audit_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_REAL_DOMAINS",
    )
    auth_boundary_audit_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_REAL_URLS",
    )
    auth_boundary_audit_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_REPORT_CONTENTS",
    )
    auth_boundary_audit_allow_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_ALLOW_PRIVATE_PATHS",
    )
    auth_boundary_audit_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_FAIL_CLOSED",
    )
    auth_boundary_audit_max_findings: int = Field(
        default=300,
        ge=1,
        le=1000,
        validation_alias="PROCORE_INTAKE_AUTH_BOUNDARY_AUDIT_MAX_FINDINGS",
    )
    intake_review_workspace_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_ENABLED",
    )
    intake_review_workspace_page_size: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_PAGE_SIZE",
    )
    intake_review_workspace_max_page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_MAX_PAGE_SIZE",
    )
    intake_review_workspace_default_sort: Literal[
        "received_at_desc",
        "received_at_asc",
        "updated_at_desc",
        "updated_at_asc",
        "tool_asc",
        "tool_desc",
    ] = Field(
        default="received_at_desc",
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_DEFAULT_SORT",
    )
    intake_review_workspace_include_attachment_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_INCLUDE_ATTACHMENT_SUMMARY",
    )
    intake_review_workspace_include_source_context: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_INCLUDE_SOURCE_CONTEXT",
    )
    intake_review_workspace_mask_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_MASK_SOURCE_IDS",
    )
    intake_review_workspace_hash_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_HASH_SOURCE_IDS",
    )
    intake_review_workspace_expose_raw_payloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_EXPOSE_RAW_PAYLOADS",
    )
    intake_review_workspace_expose_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_EXPOSE_PRIVATE_PATHS",
    )
    intake_review_workspace_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_REVIEW_WORKSPACE_FAIL_CLOSED",
    )
    intake_lifecycle_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_LIFECYCLE_ENABLED"
    )
    intake_lifecycle_default_status: Literal[
        "new", "in_review", "reviewed", "needs_follow_up", "ignored"
    ] = Field(
        default="new",
        validation_alias="PROCORE_INTAKE_LIFECYCLE_DEFAULT_STATUS",
    )
    intake_lifecycle_require_reason: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_REQUIRE_REASON",
    )
    intake_lifecycle_allow_free_text_notes: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_ALLOW_FREE_TEXT_NOTES",
    )
    intake_lifecycle_max_reason_length: int = Field(
        default=120,
        ge=1,
        le=500,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_MAX_REASON_LENGTH",
    )
    intake_lifecycle_max_events_per_record: int = Field(
        default=100,
        ge=1,
        le=1000,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_MAX_EVENTS_PER_RECORD",
    )
    intake_lifecycle_mask_actor: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_LIFECYCLE_MASK_ACTOR"
    )
    intake_lifecycle_hash_actor: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_LIFECYCLE_HASH_ACTOR"
    )
    intake_lifecycle_expose_raw_payloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_EXPOSE_RAW_PAYLOADS",
    )
    intake_lifecycle_expose_source_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_EXPOSE_SOURCE_IDS",
    )
    intake_lifecycle_expose_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LIFECYCLE_EXPOSE_PRIVATE_PATHS",
    )
    intake_lifecycle_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_LIFECYCLE_FAIL_CLOSED"
    )
    triage_queue_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_ENABLED"
    )
    triage_queue_page_size: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_PAGE_SIZE",
    )
    triage_queue_max_page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_MAX_PAGE_SIZE",
    )
    triage_queue_default_sort: Literal[
        "priority_desc",
        "priority_asc",
        "received_at_desc",
        "received_at_asc",
        "lifecycle_status_asc",
        "lifecycle_status_desc",
        "tool_asc",
        "tool_desc",
    ] = Field(
        default="priority_desc",
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_DEFAULT_SORT",
    )
    triage_queue_include_lifecycle: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_INCLUDE_LIFECYCLE",
    )
    triage_queue_include_attachment_signals: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_INCLUDE_ATTACHMENT_SIGNALS",
    )
    triage_queue_include_source_context_signals: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_INCLUDE_SOURCE_CONTEXT_SIGNALS",
    )
    triage_queue_recent_hours: int = Field(
        default=72,
        ge=1,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_RECENT_HOURS",
    )
    triage_queue_older_than_hours: int = Field(
        default=168,
        ge=1,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_OLDER_THAN_HOURS",
    )
    triage_queue_mask_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_MASK_SOURCE_IDS",
    )
    triage_queue_hash_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_HASH_SOURCE_IDS",
    )
    triage_queue_expose_raw_payloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_EXPOSE_RAW_PAYLOADS",
    )
    triage_queue_expose_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_EXPOSE_PRIVATE_PATHS",
    )
    triage_queue_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_TRIAGE_QUEUE_FAIL_CLOSED",
    )
    attachment_review_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_ENABLED",
    )
    attachment_review_page_size: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_PAGE_SIZE",
    )
    attachment_review_max_page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_MAX_PAGE_SIZE",
    )
    attachment_review_default_sort: Literal[
        "record_received_at_desc",
        "record_received_at_asc",
        "attachment_count_desc",
        "attachment_count_asc",
        "tool_asc",
        "tool_desc",
        "storage_status_asc",
        "storage_status_desc",
    ] = Field(
        default="record_received_at_desc",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_DEFAULT_SORT",
    )
    attachment_review_include_manifest_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_INCLUDE_MANIFEST_SUMMARY",
    )
    attachment_review_include_storage_status: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_INCLUDE_STORAGE_STATUS",
    )
    attachment_review_include_checksum_status: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_INCLUDE_CHECKSUM_STATUS",
    )
    attachment_review_mask_attachment_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_MASK_ATTACHMENT_IDS",
    )
    attachment_review_hash_attachment_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_HASH_ATTACHMENT_IDS",
    )
    attachment_review_expose_source_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_SOURCE_URLS",
    )
    attachment_review_expose_signed_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_SIGNED_URLS",
    )
    attachment_review_expose_storage_keys: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_STORAGE_KEYS",
    )
    attachment_review_expose_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_PRIVATE_PATHS",
    )
    attachment_review_expose_original_filenames: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_ORIGINAL_FILENAMES",
    )
    attachment_review_expose_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_EXPOSE_CONTENTS",
    )
    attachment_review_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_ATTACHMENT_REVIEW_FAIL_CLOSED",
    )
    export_pack_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_ENABLED",
    )
    export_pack_output_root: Path = Field(
        default=Path("./operator-export-output"),
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_OUTPUT_ROOT",
    )
    export_pack_default_formats: str = Field(
        default="json,md,csv",
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_DEFAULT_FORMATS",
    )
    export_pack_max_records: int = Field(
        default=1000,
        ge=1,
        le=10000,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_MAX_RECORDS",
    )
    export_pack_include_intake_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_INCLUDE_INTAKE_SUMMARY",
    )
    export_pack_include_lifecycle_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_INCLUDE_LIFECYCLE_SUMMARY",
    )
    export_pack_include_triage_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_INCLUDE_TRIAGE_SUMMARY",
    )
    export_pack_include_attachment_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_INCLUDE_ATTACHMENT_SUMMARY",
    )
    export_pack_include_event_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_INCLUDE_EVENT_SUMMARY",
    )
    export_pack_mask_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_MASK_SOURCE_IDS",
    )
    export_pack_hash_source_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_HASH_SOURCE_IDS",
    )
    export_pack_expose_raw_payloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_RAW_PAYLOADS",
    )
    export_pack_expose_source_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_SOURCE_URLS",
    )
    export_pack_expose_signed_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_SIGNED_URLS",
    )
    export_pack_expose_storage_keys: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_STORAGE_KEYS",
    )
    export_pack_expose_private_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_PRIVATE_PATHS",
    )
    export_pack_expose_original_filenames: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_ORIGINAL_FILENAMES",
    )
    export_pack_expose_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_EXPOSE_CONTENTS",
    )
    export_pack_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EXPORT_PACK_FAIL_CLOSED",
    )
    sandbox_smoke_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_ENABLED",
    )
    sandbox_smoke_require_confirmation: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_REQUIRE_CONFIRMATION",
    )
    sandbox_smoke_confirmation_phrase: str = Field(
        default="I_UNDERSTAND_THIS_IS_READ_ONLY_SANDBOX_ONLY",
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_CONFIRMATION_PHRASE",
    )
    sandbox_smoke_allow_production: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_ALLOW_PRODUCTION",
    )
    sandbox_smoke_max_records: int = Field(
        default=3,
        ge=1,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_MAX_RECORDS",
    )
    sandbox_smoke_output_root: Path = Field(
        default=Path("./smoke-output"),
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_OUTPUT_ROOT",
    )
    sandbox_smoke_write_report: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_WRITE_REPORT",
    )
    sandbox_smoke_attachment_downloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_ATTACHMENT_DOWNLOADS",
    )
    sandbox_smoke_connection_id: int | None = Field(
        default=None,
        ge=1,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_CONNECTION_ID",
    )
    sandbox_smoke_project_id: str | None = Field(
        default=None,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_PROJECT_ID",
    )
    sandbox_smoke_company_id: str | None = Field(
        default=None,
        validation_alias="PROCORE_INTAKE_SANDBOX_SMOKE_COMPANY_ID",
    )
    sandbox_read_validation_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_ENABLED",
    )
    sandbox_read_validation_confirmation: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_CONFIRMATION",
    )
    sandbox_read_validation_require_sandbox: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_REQUIRE_SANDBOX",
    )
    sandbox_read_validation_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_FAIL_CLOSED",
    )
    sandbox_read_validation_max_projects: int = Field(
        default=3,
        ge=1,
        le=3,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_MAX_PROJECTS",
    )
    sandbox_read_validation_max_items_per_tool: int = Field(
        default=5,
        ge=1,
        le=5,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_MAX_ITEMS_PER_TOOL",
    )
    sandbox_read_validation_max_pages: int = Field(
        default=2,
        ge=1,
        le=2,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_MAX_PAGES",
    )
    sandbox_read_validation_timeout_seconds: int = Field(
        default=20,
        ge=1,
        le=20,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_TIMEOUT_SECONDS",
    )
    sandbox_read_validation_include_details: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_INCLUDE_DETAILS",
    )
    sandbox_read_validation_include_attachments: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_INCLUDE_ATTACHMENTS",
    )
    sandbox_read_validation_store_raw: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_STORE_RAW",
    )
    sandbox_read_validation_output_root: Path = Field(
        default=Path("./sandbox-read-output"),
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_OUTPUT_ROOT",
    )
    sandbox_read_validation_require_allowed_scope: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_REQUIRE_ALLOWED_SCOPE",
    )
    sandbox_read_validation_mask_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_MASK_IDS",
    )
    sandbox_read_validation_hash_ids: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_HASH_IDS",
    )
    sandbox_read_validation_allowed_tools: str = Field(
        default="rfis,submittals",
        validation_alias="PROCORE_INTAKE_SANDBOX_READ_VALIDATION_ALLOWED_TOOLS",
    )
    sandbox_evidence_linkage_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ENABLED",
    )
    sandbox_evidence_linkage_output_root: Path = Field(
        default=Path("./sandbox-evidence-output"),
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_OUTPUT_ROOT",
    )
    sandbox_evidence_linkage_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_REQUIRE_PLACEHOLDERS",
    )
    sandbox_evidence_linkage_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ALLOW_REAL_IDS",
    )
    sandbox_evidence_linkage_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ALLOW_REAL_IDENTITIES",
    )
    sandbox_evidence_linkage_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ALLOW_REAL_DOMAINS",
    )
    sandbox_evidence_linkage_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ALLOW_REPORT_CONTENTS",
    )
    sandbox_evidence_linkage_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_ALLOW_ABSOLUTE_PATHS",
    )
    sandbox_evidence_linkage_max_refs: int = Field(
        default=20,
        ge=1,
        le=20,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_MAX_REFS",
    )
    sandbox_evidence_linkage_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SANDBOX_EVIDENCE_LINKAGE_FAIL_CLOSED",
    )
    customer_deployment_pattern_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_CUSTOMER_DEPLOYMENT_PATTERN_ENABLED",
    )
    customer_profile_output_root: Path = Field(
        default=Path("./customer-output"),
        validation_alias="PROCORE_INTAKE_CUSTOMER_PROFILE_OUTPUT_ROOT",
    )
    customer_profile_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_CUSTOMER_PROFILE_REQUIRE_PLACEHOLDERS",
    )
    customer_profile_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_CUSTOMER_PROFILE_ALLOW_REAL_IDS",
    )
    customer_profile_max_projects: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_CUSTOMER_PROFILE_MAX_PROJECTS",
    )
    customer_profile_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_CUSTOMER_PROFILE_FAIL_CLOSED",
    )
    operator_diagnostics_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_ENABLED",
    )
    operator_diagnostics_redaction_strict: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_REDACTION_STRICT",
    )
    operator_diagnostics_include_db_counts: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_INCLUDE_DB_COUNTS",
    )
    operator_diagnostics_include_route_inventory: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_INCLUDE_ROUTE_INVENTORY",
    )
    operator_diagnostics_include_dependency_inventory: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_INCLUDE_DEPENDENCY_INVENTORY",
    )
    operator_diagnostics_include_config_summary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_INCLUDE_CONFIG_SUMMARY",
    )
    operator_diagnostics_include_env_key_names: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_INCLUDE_ENV_KEY_NAMES",
    )
    operator_diagnostics_allow_local_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_ALLOW_LOCAL_PATHS",
    )
    operator_diagnostics_max_findings: int = Field(
        default=100,
        ge=1,
        le=1000,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_MAX_FINDINGS",
    )
    operator_diagnostics_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_OPERATOR_DIAGNOSTICS_FAIL_CLOSED",
    )
    support_bundle_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_ENABLED",
    )
    support_bundle_output_root: Path = Field(
        default=Path("./support-output"),
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_OUTPUT_ROOT",
    )
    support_bundle_max_files: int = Field(
        default=10,
        ge=1,
        le=20,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_MAX_FILES",
    )
    support_bundle_write_json: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_WRITE_JSON",
    )
    support_bundle_write_markdown: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_WRITE_MARKDOWN",
    )
    support_bundle_include_raw_logs: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_INCLUDE_RAW_LOGS",
    )
    support_bundle_include_db_file: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_INCLUDE_DB_FILE",
    )
    support_bundle_include_attachments: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_INCLUDE_ATTACHMENTS",
    )
    support_bundle_include_payloads: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_SUPPORT_BUNDLE_INCLUDE_PAYLOADS",
    )
    pilot_readiness_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_ENABLED",
    )
    pilot_readiness_output_root: Path = Field(
        default=Path("./pilot-readiness-output"),
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_OUTPUT_ROOT",
    )
    pilot_readiness_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_PLACEHOLDERS",
    )
    pilot_readiness_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_ALLOW_REAL_IDS",
    )
    pilot_readiness_allow_production: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_ALLOW_PRODUCTION",
    )
    pilot_readiness_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_FAIL_CLOSED",
    )
    pilot_readiness_require_sandbox_smoke: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_SANDBOX_SMOKE",
    )
    pilot_readiness_require_dmsa_onboarding: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_DMSA_ONBOARDING",
    )
    pilot_readiness_require_admin_auth: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_ADMIN_AUTH",
    )
    pilot_readiness_require_migration_safety: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_MIGRATION_SAFETY",
    )
    pilot_readiness_require_storage_review: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_STORAGE_REVIEW",
    )
    pilot_readiness_require_webhook_review: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_WEBHOOK_REVIEW",
    )
    pilot_readiness_require_support_diagnostics: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_SUPPORT_DIAGNOSTICS",
    )
    pilot_readiness_require_rollback_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_ROLLBACK_PLAN",
    )
    pilot_readiness_require_operator_approvals: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_READINESS_REQUIRE_OPERATOR_APPROVALS",
    )
    private_evidence_pattern_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_PATTERN_ENABLED",
    )
    private_evidence_output_root: Path = Field(
        default=Path("./private-evidence-output"),
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_OUTPUT_ROOT",
    )
    private_evidence_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_REQUIRE_PLACEHOLDERS",
    )
    private_evidence_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_ALLOW_REAL_IDS",
    )
    private_evidence_allow_file_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_ALLOW_FILE_CONTENTS",
    )
    private_evidence_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_ALLOW_ABSOLUTE_PATHS",
    )
    private_evidence_max_items: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_MAX_ITEMS",
    )
    private_evidence_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_EVIDENCE_FAIL_CLOSED",
    )
    evidence_review_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_ENABLED",
    )
    evidence_review_output_root: Path = Field(
        default=Path("./evidence-review-output"),
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_OUTPUT_ROOT",
    )
    evidence_review_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_REQUIRE_PLACEHOLDERS",
    )
    evidence_review_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_ALLOW_REAL_IDENTITIES",
    )
    evidence_review_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_ALLOW_REAL_IDS",
    )
    evidence_review_allow_file_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_ALLOW_FILE_CONTENTS",
    )
    evidence_review_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_ALLOW_ABSOLUTE_PATHS",
    )
    evidence_review_default_expiry_days: int = Field(
        default=30,
        ge=1,
        le=90,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_DEFAULT_EXPIRY_DAYS",
    )
    evidence_review_max_expiry_days: int = Field(
        default=90,
        ge=1,
        le=365,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_MAX_EXPIRY_DAYS",
    )
    evidence_review_warn_within_days: int = Field(
        default=7,
        ge=0,
        le=90,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_WARN_WITHIN_DAYS",
    )
    evidence_review_max_items: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_MAX_ITEMS",
    )
    evidence_review_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_EVIDENCE_REVIEW_FAIL_CLOSED",
    )
    pilot_approval_packet_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ENABLED",
    )
    pilot_approval_packet_output_root: Path = Field(
        default=Path("./pilot-approval-output"),
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_OUTPUT_ROOT",
    )
    pilot_approval_packet_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_PLACEHOLDERS",
    )
    pilot_approval_packet_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ALLOW_REAL_IDENTITIES",
    )
    pilot_approval_packet_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ALLOW_REAL_IDS",
    )
    pilot_approval_packet_allow_file_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ALLOW_FILE_CONTENTS",
    )
    pilot_approval_packet_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ALLOW_ABSOLUTE_PATHS",
    )
    pilot_approval_packet_allow_production: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_ALLOW_PRODUCTION",
    )
    pilot_approval_packet_require_go_decision: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_GO_DECISION",
    )
    pilot_approval_packet_require_no_expired_evidence: bool = Field(
        default=True,
        validation_alias=("PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_NO_EXPIRED_EVIDENCE"),
    )
    pilot_approval_packet_require_limitations_section: bool = Field(
        default=True,
        validation_alias=("PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_LIMITATIONS_SECTION"),
    )
    pilot_approval_packet_require_rollback_conditions: bool = Field(
        default=True,
        validation_alias=("PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_ROLLBACK_CONDITIONS"),
    )
    pilot_approval_packet_require_signoff_placeholders: bool = Field(
        default=True,
        validation_alias=("PROCORE_INTAKE_PILOT_APPROVAL_PACKET_REQUIRE_SIGNOFF_PLACEHOLDERS"),
    )
    pilot_approval_packet_max_approvers: int = Field(
        default=10,
        ge=1,
        le=10,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_MAX_APPROVERS",
    )
    pilot_approval_packet_max_conditions: int = Field(
        default=50,
        ge=1,
        le=50,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_MAX_CONDITIONS",
    )
    pilot_approval_packet_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PILOT_APPROVAL_PACKET_FAIL_CLOSED",
    )
    usage_mode: str = Field(default="demo", validation_alias="PROCORE_INTAKE_USAGE_MODE")
    allowed_usage_modes: str = Field(
        default="demo,sandbox,pilot",
        validation_alias="PROCORE_INTAKE_ALLOWED_USAGE_MODES",
    )
    mode_doctor_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_MODE_DOCTOR_ENABLED"
    )
    mode_doctor_strict_redaction: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MODE_DOCTOR_STRICT_REDACTION",
    )
    mode_doctor_include_demo: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MODE_DOCTOR_INCLUDE_DEMO",
    )
    mode_doctor_include_sandbox: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MODE_DOCTOR_INCLUDE_SANDBOX",
    )
    mode_doctor_include_pilot: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MODE_DOCTOR_INCLUDE_PILOT",
    )
    mode_doctor_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MODE_DOCTOR_FAIL_CLOSED",
    )
    demo_mode_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DEMO_MODE_ENABLED"
    )
    sandbox_mode_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SANDBOX_MODE_ENABLED"
    )
    pilot_mode_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_PILOT_MODE_ENABLED"
    )
    mode_report_output_root: Path = Field(
        default=Path("./mode-output"),
        validation_alias="PROCORE_INTAKE_MODE_REPORT_OUTPUT_ROOT",
    )
    private_workspace_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ENABLED",
    )
    private_workspace_root: Path = Field(
        default=Path("./private-workspace"),
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ROOT",
    )
    private_workspace_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_REQUIRE_PLACEHOLDERS",
    )
    private_workspace_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ALLOW_REAL_IDENTITIES",
    )
    private_workspace_allow_real_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ALLOW_REAL_IDS",
    )
    private_workspace_allow_file_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ALLOW_FILE_CONTENTS",
    )
    private_workspace_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_ALLOW_ABSOLUTE_PATHS",
    )
    private_workspace_max_files: int = Field(
        default=100,
        ge=1,
        le=100,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_MAX_FILES",
    )
    private_workspace_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_PRIVATE_WORKSPACE_FAIL_CLOSED",
    )
    storage_provider: Literal[
        "disabled",
        "local",
        "test",
        "external_placeholder",
        "s3",
        "azure_blob",
        "gcs",
    ] = Field(default="local", validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER")
    storage_provider_strict_redaction: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_STRICT_REDACTION",
    )
    storage_provider_allow_local: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_ALLOW_LOCAL",
    )
    storage_provider_allow_cloud: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_ALLOW_CLOUD",
    )
    storage_provider_cloud_network_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_NETWORK_ENABLED",
    )
    storage_provider_cloud_confirmation: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_CONFIRMATION",
    )
    storage_provider_cloud_timeout_seconds: int = Field(
        default=20,
        ge=1,
        le=60,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_TIMEOUT_SECONDS",
    )
    storage_provider_cloud_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_FAIL_CLOSED",
    )
    storage_provider_cloud_health_network_check: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_HEALTH_NETWORK_CHECK",
    )
    storage_provider_cloud_allow_list: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_ALLOW_LIST",
    )
    storage_provider_cloud_allow_delete: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_ALLOW_DELETE",
    )
    storage_provider_cloud_allow_overwrite: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_ALLOW_OVERWRITE",
    )
    storage_provider_cloud_allow_presigned_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_CLOUD_ALLOW_PRESIGNED_URLS",
    )
    storage_provider_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_STORAGE_PROVIDER_FAIL_CLOSED",
    )
    local_storage_root: Path = Field(
        default=Path("./private-workspace/storage"),
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_ROOT",
    )
    local_storage_require_private_root: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_REQUIRE_PRIVATE_ROOT",
    )
    local_storage_allow_absolute_root: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_ALLOW_ABSOLUTE_ROOT",
    )
    local_storage_max_bytes: int = Field(
        default=10485760,
        ge=1,
        le=104857600,
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_MAX_BYTES",
    )
    local_storage_allowed_extensions: str = Field(
        default=".txt,.json,.md,.csv",
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_ALLOWED_EXTENSIONS",
    )
    local_storage_block_binary: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_BLOCK_BINARY",
    )
    local_storage_overwrite: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_LOCAL_STORAGE_OVERWRITE",
    )
    s3_storage_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_S3_STORAGE_ENABLED",
    )
    s3_region_ref: str = Field(
        default="AWS_REGION",
        validation_alias="PROCORE_INTAKE_S3_REGION_REF",
    )
    s3_bucket_ref: str = Field(
        default="S3_BUCKET_NAME",
        validation_alias="PROCORE_INTAKE_S3_BUCKET_REF",
    )
    s3_key_prefix: str = Field(
        default="procore-intake-placeholder",
        validation_alias="PROCORE_INTAKE_S3_KEY_PREFIX",
    )
    s3_require_region: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_S3_REQUIRE_REGION",
    )
    s3_allow_bucket_arns: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_S3_ALLOW_BUCKET_ARNS",
    )
    s3_allow_s3_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_S3_ALLOW_S3_URLS",
    )
    azure_blob_storage_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AZURE_BLOB_STORAGE_ENABLED",
    )
    azure_storage_account_ref: str = Field(
        default="AZURE_STORAGE_ACCOUNT_NAME",
        validation_alias="PROCORE_INTAKE_AZURE_STORAGE_ACCOUNT_REF",
    )
    azure_blob_container_ref: str = Field(
        default="AZURE_BLOB_CONTAINER_NAME",
        validation_alias="PROCORE_INTAKE_AZURE_BLOB_CONTAINER_REF",
    )
    azure_blob_prefix: str = Field(
        default="procore-intake-placeholder",
        validation_alias="PROCORE_INTAKE_AZURE_BLOB_PREFIX",
    )
    azure_blob_use_default_credential: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_AZURE_BLOB_USE_DEFAULT_CREDENTIAL",
    )
    azure_blob_allow_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_AZURE_BLOB_ALLOW_URLS",
    )
    gcs_storage_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_GCS_STORAGE_ENABLED",
    )
    gcs_project_id_ref: str = Field(
        default="GCP_PROJECT_ID",
        validation_alias="PROCORE_INTAKE_GCS_PROJECT_ID_REF",
    )
    gcs_bucket_ref: str = Field(
        default="GCS_BUCKET_NAME",
        validation_alias="PROCORE_INTAKE_GCS_BUCKET_REF",
    )
    gcs_key_prefix: str = Field(
        default="procore-intake-placeholder",
        validation_alias="PROCORE_INTAKE_GCS_KEY_PREFIX",
    )
    gcs_allow_resource_names: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_GCS_ALLOW_RESOURCE_NAMES",
    )
    gcs_allow_gs_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_GCS_ALLOW_GS_URLS",
    )
    database_provider: Literal["sqlite", "postgres"] = Field(
        default="sqlite", validation_alias="PROCORE_INTAKE_DATABASE_PROVIDER"
    )
    database_provider_strict_redaction: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DATABASE_PROVIDER_STRICT_REDACTION",
    )
    database_allow_sqlite: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DATABASE_ALLOW_SQLITE"
    )
    database_allow_postgres: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DATABASE_ALLOW_POSTGRES"
    )
    database_external_connect_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DATABASE_EXTERNAL_CONNECT_ENABLED",
    )
    database_external_connect_confirmation: str = Field(
        default="",
        validation_alias="PROCORE_INTAKE_DATABASE_EXTERNAL_CONNECT_CONFIRMATION",
    )
    database_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DATABASE_FAIL_CLOSED"
    )
    database_url_ref: str = Field(
        default="DATABASE_URL", validation_alias="PROCORE_INTAKE_DATABASE_URL_REF"
    )
    database_url_source: Literal["env", "file", "secret_provider"] = Field(
        default="env", validation_alias="PROCORE_INTAKE_DATABASE_URL_SOURCE"
    )
    database_require_secret_ref_for_external: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DATABASE_REQUIRE_SECRET_REF_FOR_EXTERNAL",
    )
    database_mask_hostnames: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DATABASE_MASK_HOSTNAMES"
    )
    database_mask_usernames: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DATABASE_MASK_USERNAMES"
    )
    postgres_required_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRED_FOR_PILOT"
    )
    postgres_min_version: int = Field(
        default=14, ge=12, validation_alias="PROCORE_INTAKE_POSTGRES_MIN_VERSION"
    )
    postgres_require_ssl: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_SSL"
    )
    postgres_require_backup_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_BACKUP_PLAN",
    )
    postgres_require_rollback_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_ROLLBACK_PLAN",
    )
    postgres_runtime_enabled: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_ENABLED"
    )
    postgres_runtime_confirmation: str = Field(
        default="", validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_CONFIRMATION"
    )
    postgres_runtime_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_FAIL_CLOSED"
    )
    postgres_runtime_timeout_seconds: int = Field(
        default=20, gt=0, validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_TIMEOUT_SECONDS"
    )
    postgres_runtime_statement_timeout_seconds: int = Field(
        default=10,
        gt=0,
        validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_STATEMENT_TIMEOUT_SECONDS",
    )
    postgres_runtime_connectivity_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_CONNECTIVITY_ENABLED",
    )
    postgres_runtime_migrations_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_MIGRATIONS_ENABLED",
    )
    postgres_runtime_backup_check_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_BACKUP_CHECK_ENABLED",
    )
    postgres_runtime_restore_check_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_POSTGRES_RUNTIME_RESTORE_CHECK_ENABLED",
    )
    postgres_pool_size: int = Field(
        default=5, ge=1, validation_alias="PROCORE_INTAKE_POSTGRES_POOL_SIZE"
    )
    postgres_max_overflow: int = Field(
        default=5, ge=0, validation_alias="PROCORE_INTAKE_POSTGRES_MAX_OVERFLOW"
    )
    postgres_pool_timeout_seconds: int = Field(
        default=30, gt=0, validation_alias="PROCORE_INTAKE_POSTGRES_POOL_TIMEOUT_SECONDS"
    )
    postgres_pool_recycle_seconds: int = Field(
        default=1800, ge=0, validation_alias="PROCORE_INTAKE_POSTGRES_POOL_RECYCLE_SECONDS"
    )
    postgres_pool_pre_ping: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_POSTGRES_POOL_PRE_PING"
    )
    postgres_require_managed_backup_ref: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_MANAGED_BACKUP_REF",
    )
    postgres_require_restore_drill_ref: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_RESTORE_DRILL_REF",
    )
    postgres_require_maintenance_window_ref: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_MAINTENANCE_WINDOW_REF",
    )
    postgres_require_rollback_ref: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_REQUIRE_ROLLBACK_REF",
    )
    postgres_operation_output_root: Path = Field(
        default=Path("./postgres-ops-output"),
        validation_alias="PROCORE_INTAKE_POSTGRES_OPERATION_OUTPUT_ROOT",
    )
    postgres_operation_store_raw: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_POSTGRES_OPERATION_STORE_RAW"
    )
    postgres_operation_mask_hosts: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_POSTGRES_OPERATION_MASK_HOSTS"
    )
    postgres_operation_mask_database_names: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_OPERATION_MASK_DATABASE_NAMES",
    )
    postgres_operation_mask_usernames: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_POSTGRES_OPERATION_MASK_USERNAMES",
    )
    migration_execution_plan_required: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MIGRATION_EXECUTION_PLAN_REQUIRED",
    )
    migration_execution_output_root: Path = Field(
        default=Path("./migration-output"),
        validation_alias="PROCORE_INTAKE_MIGRATION_EXECUTION_OUTPUT_ROOT",
    )
    migration_execution_allow_external: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_MIGRATION_EXECUTION_ALLOW_EXTERNAL",
    )
    migration_execution_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_MIGRATION_EXECUTION_FAIL_CLOSED",
    )
    deployment_recipes_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPES_ENABLED"
    )
    hosted_deployment_templates_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_TEMPLATES_ENABLED",
    )
    hosted_deployment_output_root: Path = Field(
        default=Path("./hosted-deployment-output"),
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_OUTPUT_ROOT",
    )
    hosted_deployment_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_REQUIRE_PLACEHOLDERS",
    )
    hosted_deployment_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_ALLOW_REAL_DOMAINS",
    )
    hosted_deployment_allow_real_infra_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_ALLOW_REAL_INFRA_IDS",
    )
    hosted_deployment_allow_real_registry_refs: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_ALLOW_REAL_REGISTRY_REFS",
    )
    hosted_deployment_allow_real_cloud_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_ALLOW_REAL_CLOUD_IDS",
    )
    hosted_deployment_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_ALLOW_ABSOLUTE_PATHS",
    )
    hosted_deployment_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_DEPLOYMENT_FAIL_CLOSED",
    )
    https_webhook_planning_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_PLANNING_ENABLED",
    )
    https_webhook_planning_output_root: Path = Field(
        default=Path("./https-webhook-output"),
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_PLANNING_OUTPUT_ROOT",
    )
    https_webhook_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_PLACEHOLDERS",
    )
    https_webhook_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_ALLOW_REAL_DOMAINS",
    )
    https_webhook_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_ALLOW_REAL_URLS",
    )
    https_webhook_allow_cert_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_ALLOW_CERT_CONTENTS",
    )
    https_webhook_allow_dns_records: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_ALLOW_DNS_RECORDS",
    )
    https_webhook_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_ALLOW_ABSOLUTE_PATHS",
    )
    https_webhook_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_FAIL_CLOSED",
    )
    https_webhook_expected_path: str = Field(
        default="/webhooks/procore",
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_EXPECTED_PATH",
    )
    https_webhook_require_https: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_HTTPS",
    )
    https_webhook_require_public_ingress: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_PUBLIC_INGRESS",
    )
    https_webhook_require_tls_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_TLS_PLAN",
    )
    https_webhook_require_dns_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_DNS_PLAN",
    )
    https_webhook_require_signature_secret_ref: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_SIGNATURE_SECRET_REF",
    )
    https_webhook_require_replay_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_REPLAY_PLAN",
    )
    https_webhook_require_disable_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_DISABLE_PLAN",
    )
    https_webhook_require_rollback_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_ROLLBACK_PLAN",
    )
    https_webhook_require_event_queue: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HTTPS_WEBHOOK_REQUIRE_EVENT_QUEUE",
    )
    hosted_pilot_dry_run_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ENABLED",
    )
    hosted_pilot_dry_run_output_root: Path = Field(
        default=Path("./hosted-pilot-dry-run-output"),
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_OUTPUT_ROOT",
    )
    hosted_pilot_dry_run_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_REQUIRE_PLACEHOLDERS",
    )
    hosted_pilot_dry_run_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_REAL_IDENTITIES",
    )
    hosted_pilot_dry_run_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_REAL_DOMAINS",
    )
    hosted_pilot_dry_run_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_REAL_URLS",
    )
    hosted_pilot_dry_run_allow_real_infra_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_REAL_INFRA_IDS",
    )
    hosted_pilot_dry_run_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_REPORT_CONTENTS",
    )
    hosted_pilot_dry_run_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_ALLOW_ABSOLUTE_PATHS",
    )
    hosted_pilot_dry_run_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_FAIL_CLOSED",
    )
    hosted_pilot_dry_run_max_refs: int = Field(
        default=50,
        ge=1,
        le=200,
        validation_alias="PROCORE_INTAKE_HOSTED_PILOT_DRY_RUN_MAX_REFS",
    )
    final_public_readiness_enabled: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ENABLED",
    )
    final_public_readiness_output_root: Path = Field(
        default=Path("./final-readiness-output"),
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_OUTPUT_ROOT",
    )
    final_public_readiness_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_REQUIRE_PLACEHOLDERS",
    )
    final_public_readiness_allow_real_identities: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_REAL_IDENTITIES",
    )
    final_public_readiness_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_REAL_DOMAINS",
    )
    final_public_readiness_allow_real_urls: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_REAL_URLS",
    )
    final_public_readiness_allow_real_infra_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_REAL_INFRA_IDS",
    )
    final_public_readiness_allow_report_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_REPORT_CONTENTS",
    )
    final_public_readiness_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_ALLOW_ABSOLUTE_PATHS",
    )
    final_public_readiness_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_FAIL_CLOSED",
    )
    final_public_readiness_max_findings: int = Field(
        default=250,
        ge=1,
        le=1000,
        validation_alias="PROCORE_INTAKE_FINAL_PUBLIC_READINESS_MAX_FINDINGS",
    )
    deployment_recipe_output_root: Path = Field(
        default=Path("./deployment-output"),
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_OUTPUT_ROOT",
    )
    deployment_recipe_require_placeholders: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_REQUIRE_PLACEHOLDERS",
    )
    deployment_recipe_allow_real_domains: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_ALLOW_REAL_DOMAINS",
    )
    deployment_recipe_allow_real_infra_ids: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_ALLOW_REAL_INFRA_IDS",
    )
    deployment_recipe_allow_cert_contents: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_ALLOW_CERT_CONTENTS",
    )
    deployment_recipe_allow_absolute_paths: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_ALLOW_ABSOLUTE_PATHS",
    )
    deployment_recipe_fail_closed: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_RECIPE_FAIL_CLOSED",
    )
    deployment_target: Literal["docker_local", "docker_vps", "managed_paas", "generic_cloud"] = (
        Field(
            default="docker_local",
            validation_alias="PROCORE_INTAKE_DEPLOYMENT_TARGET",
        )
    )
    deployment_allowed_targets: str = Field(
        default="docker_local,docker_vps,managed_paas,generic_cloud",
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_ALLOWED_TARGETS",
    )
    deployment_require_https_for_webhooks: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_REQUIRE_HTTPS_FOR_WEBHOOKS",
    )
    deployment_require_public_ingress_for_webhooks: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_REQUIRE_PUBLIC_INGRESS_FOR_WEBHOOKS",
    )
    deployment_require_backup_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_REQUIRE_BACKUP_PLAN",
    )
    deployment_require_rollback_plan: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_REQUIRE_ROLLBACK_PLAN",
    )
    deployment_require_operator_runbook: bool = Field(
        default=True,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_REQUIRE_OPERATOR_RUNBOOK",
    )
    deployment_external_provisioning_enabled: bool = Field(
        default=False,
        validation_alias="PROCORE_INTAKE_DEPLOYMENT_EXTERNAL_PROVISIONING_ENABLED",
    )
    sandbox_pilot_flow_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_ENABLED"
    )
    sandbox_pilot_flow_output_root: Path = Field(
        default=Path("./sandbox-pilot-output"),
        validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_OUTPUT_ROOT",
    )
    sandbox_pilot_flow_require_placeholders: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_REQUIRE_PLACEHOLDERS"
    )
    sandbox_pilot_flow_allow_real_ids: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_ALLOW_REAL_IDS"
    )
    sandbox_pilot_flow_allow_real_identities: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_ALLOW_REAL_IDENTITIES"
    )
    sandbox_pilot_flow_allow_real_domains: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_ALLOW_REAL_DOMAINS"
    )
    sandbox_pilot_flow_allow_production: bool = Field(
        default=False, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_ALLOW_PRODUCTION"
    )
    sandbox_pilot_flow_fail_closed: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_SANDBOX_PILOT_FLOW_FAIL_CLOSED"
    )
    flow_require_demo_ready: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_DEMO_READY"
    )
    flow_require_dmsa_refs_for_sandbox: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_DMSA_REFS_FOR_SANDBOX"
    )
    flow_require_project_scope_for_sandbox: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_PROJECT_SCOPE_FOR_SANDBOX"
    )
    flow_require_admin_auth_for_sandbox: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_ADMIN_AUTH_FOR_SANDBOX"
    )
    flow_require_sandbox_smoke_before_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_SANDBOX_SMOKE_BEFORE_PILOT"
    )
    flow_require_private_workspace_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_PRIVATE_WORKSPACE_FOR_PILOT"
    )
    flow_require_secret_provider_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_SECRET_PROVIDER_FOR_PILOT"
    )
    flow_require_storage_provider_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_STORAGE_PROVIDER_FOR_PILOT"
    )
    flow_require_postgres_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_POSTGRES_FOR_PILOT"
    )
    flow_require_deployment_recipe_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_DEPLOYMENT_RECIPE_FOR_PILOT"
    )
    flow_require_evidence_review_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_EVIDENCE_REVIEW_FOR_PILOT"
    )
    flow_require_approval_packet_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_APPROVAL_PACKET_FOR_PILOT"
    )
    flow_require_rollback_for_pilot: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_FLOW_REQUIRE_ROLLBACK_FOR_PILOT"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
