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
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_ENVIRONMENT", "APP_DEPLOYMENT_ENVIRONMENT"
        ),
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
    cors_origins: str = Field(
        default="", validation_alias="PROCORE_INTAKE_CORS_ORIGINS"
    )
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
    secret_provider: Literal["env", "test", "disabled", "external_placeholder"] = Field(
        default="env",
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_SECRET_PROVIDER", "APP_SECRET_PROVIDER"
        ),
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
    webhooks_enabled: bool = Field(
        default=True, validation_alias="PROCORE_INTAKE_WEBHOOKS_ENABLED"
    )
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
    attachment_storage_provider: Literal[
        "local", "test", "disabled", "external_placeholder"
    ] = Field(
        default="local",
        validation_alias="PROCORE_INTAKE_ATTACHMENT_STORAGE_PROVIDER",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
