#!/usr/bin/env python3
from sqlalchemy import create_engine, text

from app.config import Settings, get_settings
from app.schemas.database import DatabaseProviderStatus, DatabaseSafetyCheckResult
from app.security.secret_provider_factory import build_secret_provider

CONFIRMATION = "I understand this will attempt a database connection"


def run_connectivity_check(
    settings: Settings,
    *,
    engine_factory=create_engine,
) -> DatabaseSafetyCheckResult:
    if not settings.database_external_connect_enabled:
        return DatabaseSafetyCheckResult(
            success=False,
            status=DatabaseProviderStatus.BLOCKED,
            connectivity_attempted=False,
        )
    if settings.database_external_connect_confirmation != CONFIRMATION:
        return DatabaseSafetyCheckResult(
            success=False,
            status=DatabaseProviderStatus.BLOCKED,
            connectivity_attempted=False,
        )
    try:
        provider_settings = settings.model_copy(
            update={"secret_require_prefix": False}
        )
        url = build_secret_provider(provider_settings).get_secret(
            settings.database_url_ref
        )
        engine = engine_factory(
            url,
            pool_pre_ping=False,
            connect_args={"connect_timeout": 5},
        )
        try:
            with engine.connect() as connection:
                success = connection.execute(text("SELECT 1")).scalar() == 1
        finally:
            engine.dispose()
        return DatabaseSafetyCheckResult(
            success=success,
            status=(
                DatabaseProviderStatus.READY
                if success
                else DatabaseProviderStatus.NEEDS_CONFIGURATION
            ),
            connectivity_attempted=True,
            external_calls=True,
        )
    except Exception:
        return DatabaseSafetyCheckResult(
            success=False,
            status=DatabaseProviderStatus.NEEDS_CONFIGURATION,
            connectivity_attempted=True,
            external_calls=True,
        )


def main() -> int:
    result = run_connectivity_check(get_settings())
    print(result.model_dump_json(indent=2))
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
