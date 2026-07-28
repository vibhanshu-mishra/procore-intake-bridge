from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", extra="ignore", populate_by_name=True
    )

    database_url: str = "sqlite:///./procore_intake_bridge.db"
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
            "PROCORE_INTAKE_ENVIRONMENT", "APP_PROCORE_ENVIRONMENT"
        ),
    )
    secret_provider: Literal["env"] = Field(
        default="env",
        validation_alias=AliasChoices(
            "PROCORE_INTAKE_SECRET_PROVIDER", "APP_SECRET_PROVIDER"
        ),
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
    attachment_storage_backend: Literal["local"] = Field(
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
