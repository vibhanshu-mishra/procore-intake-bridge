import json
import re
from collections.abc import Callable, Mapping
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.database_runtime import (
    PostgresBackupVerificationPlan,
    PostgresConnectivityCheckResult,
    PostgresMigrationExecutionPlan,
    PostgresPoolConfigSummary,
    PostgresRestoreDrillPlan,
    PostgresRuntimeArtifactResult,
    PostgresRuntimeDecision,
    PostgresRuntimeFinding,
    PostgresRuntimeReport,
    PostgresRuntimeRequirement,
    PostgresRuntimeStatus,
)

POSTGRES_RUNTIME_CONFIRMATION_PHRASE = (
    "I understand this may contact an external PostgreSQL database"
)
DATABASE_URL = re.compile(r"(?i)\bpostgres(?:ql)?(?:\+\w+)?://\S+")
CREDENTIAL = re.compile(
    r"(?i)\b(?:password|passwd|pwd|username|user)\s*[:=]\s*[^\s,;]+"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
SAFE_REF = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
SAFE_OUTPUT_ROOTS = {
    "postgres-ops-output",
    "postgres-runtime-output",
    "db-ops-output",
}


class DatabaseRuntimeError(RuntimeError):
    """A sanitized PostgreSQL runtime operation failed."""


class DatabaseRuntimeBlockedError(DatabaseRuntimeError):
    """A PostgreSQL runtime operation was refused before private resolution."""


def sanitize_database_runtime_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_database_runtime_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_database_runtime_value(item) for item in value]
    if isinstance(value, Path):
        return "[masked-path]"
    if isinstance(value, str):
        sanitized = DATABASE_URL.sub("[masked-database-url]", value)
        sanitized = CREDENTIAL.sub("[masked-credential]", sanitized)
        if ABSOLUTE_PATH.search(sanitized):
            return "[masked-path]"
        return sanitized
    return value


def mask_database_runtime_ref(value: str) -> str:
    ref = value.strip()
    if not ref:
        return "[database-reference-not-configured]"
    if DATABASE_URL.search(ref):
        return "[masked-database-url]"
    if SAFE_REF.fullmatch(ref):
        return f"database-ref-{ref[-4:].casefold()}"
    return "[masked-database-reference]"


def build_postgres_pool_config_summary(settings: Settings) -> PostgresPoolConfigSummary:
    return PostgresPoolConfigSummary(
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_timeout_seconds=settings.postgres_pool_timeout_seconds,
        pool_recycle_seconds=settings.postgres_pool_recycle_seconds,
        pool_pre_ping=settings.postgres_pool_pre_ping,
        connection_timeout_seconds=settings.postgres_runtime_timeout_seconds,
        statement_timeout_seconds=settings.postgres_runtime_statement_timeout_seconds,
        ssl_required=settings.postgres_require_ssl,
    )


def _requirement(name: str, required: bool, placeholder: str) -> PostgresRuntimeRequirement:
    return PostgresRuntimeRequirement(
        name=name,
        required=required,
        configured=False,
        private_reference=placeholder if required else "",
    )


def build_postgres_runtime_preflight(settings: Settings) -> list[PostgresRuntimeFinding]:
    findings: list[PostgresRuntimeFinding] = []
    if settings.database_provider != "postgres":
        findings.append(PostgresRuntimeFinding(
            code="postgres_not_selected",
            status=PostgresRuntimeStatus.NEEDS_CONFIGURATION,
            message="PostgreSQL is not the selected database provider.",
        ))
    if not settings.postgres_runtime_enabled:
        findings.append(PostgresRuntimeFinding(
            code="runtime_disabled",
            status=PostgresRuntimeStatus.NEEDS_CONFIGURATION,
            message="PostgreSQL runtime operations are disabled by default.",
        ))
    if settings.postgres_operation_store_raw:
        findings.append(PostgresRuntimeFinding(
            code="raw_output_forbidden",
            status=PostgresRuntimeStatus.BLOCKED,
            message="Raw PostgreSQL operation output must remain disabled.",
        ))
    if not (
        settings.postgres_operation_mask_hosts
        and settings.postgres_operation_mask_database_names
        and settings.postgres_operation_mask_usernames
    ):
        findings.append(PostgresRuntimeFinding(
            code="masking_required",
            status=PostgresRuntimeStatus.BLOCKED,
            message="Host, database-name, and username masking must remain enabled.",
        ))
    if not findings:
        findings.append(PostgresRuntimeFinding(
            code="offline_preflight_ready",
            status=PostgresRuntimeStatus.READY,
            message="Offline posture is ready for private operator review.",
        ))
    return findings


def build_postgres_runtime_report(settings: Settings) -> PostgresRuntimeReport:
    findings = build_postgres_runtime_preflight(settings)
    blocked = any(item.status == PostgresRuntimeStatus.BLOCKED for item in findings)
    needs_configuration = any(
        item.status == PostgresRuntimeStatus.NEEDS_CONFIGURATION for item in findings
    )
    status = (
        PostgresRuntimeStatus.BLOCKED
        if blocked
        else PostgresRuntimeStatus.NEEDS_CONFIGURATION
        if needs_configuration
        else PostgresRuntimeStatus.READY
    )
    return PostgresRuntimeReport(
        status=status,
        decision=(
            PostgresRuntimeDecision.REFUSE
            if blocked or needs_configuration
            else PostgresRuntimeDecision.ALLOW_OFFLINE
        ),
        runtime_enabled=settings.postgres_runtime_enabled,
        connectivity_enabled=settings.postgres_runtime_connectivity_enabled,
        migrations_enabled=settings.postgres_runtime_migrations_enabled,
        backup_check_enabled=settings.postgres_runtime_backup_check_enabled,
        restore_check_enabled=settings.postgres_runtime_restore_check_enabled,
        pool_config_summary=build_postgres_pool_config_summary(settings),
        findings=findings,
        recommended_next_steps=[
            "Keep the database URL in the selected private secret provider.",
            (
                "Review the maintenance, migration, backup, restore, and rollback "
                "references privately."
            ),
            "Use live status checks only during an approved operator-controlled window.",
        ],
    )


def build_postgres_migration_execution_plan(
    settings: Settings,
) -> PostgresMigrationExecutionPlan:
    return PostgresMigrationExecutionPlan(
        status=PostgresRuntimeStatus.NEEDS_CONFIGURATION,
        decision=PostgresRuntimeDecision.ALLOW_OFFLINE,
        requirements=[
            _requirement(
                "maintenance_window",
                settings.postgres_require_maintenance_window_ref,
                "MAINTENANCE_WINDOW_REF_PLACEHOLDER",
            ),
            _requirement(
                "rollback",
                settings.postgres_require_rollback_ref,
                "ROLLBACK_PLAN_REF_PLACEHOLDER",
            ),
            _requirement(
                "migration_status",
                True,
                "MIGRATION_STATUS_REF_PLACEHOLDER",
            ),
        ],
        steps=[
            "Review the private maintenance-window and rollback references.",
            "Capture a sanitized migration-status reference.",
            "Obtain a separate operator decision before any migration execution.",
            "Verify health and rollback criteria privately after an approved run.",
        ],
    )


def build_postgres_backup_verification_plan(
    settings: Settings,
) -> PostgresBackupVerificationPlan:
    return PostgresBackupVerificationPlan(
        status=PostgresRuntimeStatus.NEEDS_CONFIGURATION,
        decision=PostgresRuntimeDecision.ALLOW_OFFLINE,
        requirements=[
            _requirement(
                "managed_backup",
                settings.postgres_require_managed_backup_ref,
                "BACKUP_PLAN_REF_PLACEHOLDER",
            )
        ],
        steps=[
            "Review the managed-backup policy and retention privately.",
            "Record only a sanitized evidence reference.",
            "Do not copy backup names, logs, files, or contents into public artifacts.",
        ],
    )


def build_postgres_restore_drill_plan(settings: Settings) -> PostgresRestoreDrillPlan:
    return PostgresRestoreDrillPlan(
        status=PostgresRuntimeStatus.NEEDS_CONFIGURATION,
        decision=PostgresRuntimeDecision.ALLOW_OFFLINE,
        requirements=[
            _requirement(
                "restore_drill",
                settings.postgres_require_restore_drill_ref,
                "RESTORE_DRILL_REF_PLACEHOLDER",
            ),
            _requirement(
                "rollback",
                settings.postgres_require_rollback_ref,
                "ROLLBACK_PLAN_REF_PLACEHOLDER",
            ),
        ],
        steps=[
            "Schedule an isolated, operator-controlled restore drill.",
            "Validate application health and migration posture without publishing private details.",
            "Record only sanitized evidence and follow the private rollback procedure.",
        ],
    )


def _serialized(value: Any) -> str:
    raw = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    return json.dumps(raw, sort_keys=True)


def validate_postgres_runtime_report_safe(report: Any) -> None:
    text = _serialized(report)
    if DATABASE_URL.search(text) or CREDENTIAL.search(text) or ABSOLUTE_PATH.search(text):
        raise DatabaseRuntimeBlockedError("PostgreSQL runtime report failed safety validation.")
    forbidden_flags = (
        "db_url_exposed",
        "credentials_exposed",
        "hostnames_exposed",
        "database_names_exposed",
        "usernames_exposed",
        "query_text_exposed",
        "raw_logs_exposed",
        "dump_or_backup_contents_exposed",
        "private_paths_exposed",
    )
    raw = report.model_dump(mode="json") if hasattr(report, "model_dump") else report
    if isinstance(raw, Mapping) and any(raw.get(flag) is True for flag in forbidden_flags):
        raise DatabaseRuntimeBlockedError("PostgreSQL runtime report exposes private material.")


def render_postgres_runtime_report_markdown(report: PostgresRuntimeReport) -> str:
    validate_postgres_runtime_report_safe(report)
    return (
        "# PostgreSQL runtime posture\n\n"
        f"- Status: `{report.status}`\n"
        f"- Runtime enabled: `{str(report.runtime_enabled).lower()}`\n"
        f"- Connectivity enabled: `{str(report.connectivity_enabled).lower()}`\n"
        f"- Migration status enabled: `{str(report.migrations_enabled).lower()}`\n"
        "- External database contact attempted: `false`\n"
        "- Private database material exposed: `false`\n"
        "- This offline report does not approve a production database operation.\n"
    )


def _render_plan(title: str, steps: list[str], safety: str) -> str:
    lines = [f"# {title}", "", safety, ""]
    lines.extend(f"{index}. {step}" for index, step in enumerate(steps, 1))
    return "\n".join(lines) + "\n"


def render_postgres_migration_execution_plan_markdown(
    plan: PostgresMigrationExecutionPlan,
) -> str:
    return _render_plan(
        "PostgreSQL migration run plan",
        plan.steps,
        "Offline checklist only. It does not connect or run a migration.",
    )


def render_postgres_backup_verification_plan_markdown(
    plan: PostgresBackupVerificationPlan,
) -> str:
    return _render_plan(
        "PostgreSQL backup verification plan",
        plan.steps,
        "Offline checklist only. It does not inspect a backup or contact a database.",
    )


def render_postgres_restore_drill_plan_markdown(plan: PostgresRestoreDrillPlan) -> str:
    return _render_plan(
        "PostgreSQL restore drill plan",
        plan.steps,
        "Offline checklist only. It does not inspect a dump or perform a restore.",
    )


def write_postgres_runtime_artifacts(
    report: PostgresRuntimeReport, output_root: Path
) -> PostgresRuntimeArtifactResult:
    if output_root.is_absolute() or output_root.parts[:1] not in {
        (name,) for name in SAFE_OUTPUT_ROOTS
    }:
        raise DatabaseRuntimeBlockedError("PostgreSQL runtime output root is unsafe.")
    validate_postgres_runtime_report_safe(report)
    output_root.mkdir(parents=True, exist_ok=True)
    files = [
        "postgres-runtime.postgres-runtime-report.json",
        "postgres-runtime.postgres-runtime-report.md",
    ]
    (output_root / files[0]).write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / files[1]).write_text(
        render_postgres_runtime_report_markdown(report), encoding="utf-8"
    )
    return PostgresRuntimeArtifactResult(files=files, written=True)


def _gate(settings: Settings, enabled: bool, operation: str) -> None:
    if settings.database_provider != "postgres":
        raise DatabaseRuntimeBlockedError(
            "PostgreSQL runtime check refused: provider not selected."
        )
    if not settings.postgres_runtime_enabled:
        raise DatabaseRuntimeBlockedError("PostgreSQL runtime check refused: runtime disabled.")
    if not enabled:
        raise DatabaseRuntimeBlockedError(
            f"PostgreSQL {operation} check refused: operation disabled."
        )
    if settings.postgres_runtime_confirmation != POSTGRES_RUNTIME_CONFIRMATION_PHRASE:
        raise DatabaseRuntimeBlockedError(
            f"PostgreSQL {operation} check refused: confirmation missing."
        )
    if settings.postgres_operation_store_raw or not (
        settings.postgres_operation_mask_hosts
        and settings.postgres_operation_mask_database_names
        and settings.postgres_operation_mask_usernames
    ):
        raise DatabaseRuntimeBlockedError(
            f"PostgreSQL {operation} check refused: safe output policy is not enabled."
        )
    if not SAFE_REF.fullmatch(settings.database_url_ref.strip()):
        raise DatabaseRuntimeBlockedError(
            f"PostgreSQL {operation} check refused: private database reference is invalid."
        )


def _provider_and_url(settings: Settings, secret_provider: Any) -> tuple[Any, str]:
    if secret_provider is None:
        from app.security.secret_provider import get_secret_provider

        secret_provider = get_secret_provider(settings)
    try:
        value = secret_provider.get_secret(settings.database_url_ref)
    except Exception as exc:
        raise DatabaseRuntimeError(
            "Private database reference resolution failed safely."
        ) from exc
    if not isinstance(value, str) or not value.startswith(("postgresql://", "postgres://")):
        raise DatabaseRuntimeError("Private database reference is not a PostgreSQL URL.")
    return secret_provider, value


def _result(
    operation: str,
    status: PostgresRuntimeStatus,
    success: bool,
    message: str,
) -> PostgresConnectivityCheckResult:
    return PostgresConnectivityCheckResult(
        operation=operation,
        status=status,
        success=success,
        message=message,
        cloud_or_external_db_contact_attempted=True,
    )


def run_postgres_connectivity_check(
    settings: Settings,
    secret_provider: Any = None,
    engine_factory: Callable[..., Any] | None = None,
) -> PostgresConnectivityCheckResult:
    _gate(settings, settings.postgres_runtime_connectivity_enabled, "connectivity")
    if engine_factory is None and find_spec("psycopg") is None:
        return _result(
            "connectivity",
            PostgresRuntimeStatus.DEPENDENCY_MISSING,
            False,
            "Optional PostgreSQL driver is not installed.",
        )
    _, database_url = _provider_and_url(settings, secret_provider)
    engine = None
    try:
        if engine_factory is None:
            from sqlalchemy import create_engine

            engine_factory = create_engine
        engine = engine_factory(
            database_url,
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
            pool_timeout=settings.postgres_pool_timeout_seconds,
            pool_recycle=settings.postgres_pool_recycle_seconds,
            pool_pre_ping=settings.postgres_pool_pre_ping,
            connect_args={
                "connect_timeout": settings.postgres_runtime_timeout_seconds,
                "options": (
                    "-c statement_timeout="
                    f"{settings.postgres_runtime_statement_timeout_seconds * 1000}"
                ),
                **({"sslmode": "require"} if settings.postgres_require_ssl else {}),
            },
        )
        with engine.connect() as connection:
            from sqlalchemy import text

            connection.execute(text("SELECT 1"))
        return _result(
            "connectivity",
            PostgresRuntimeStatus.SUCCESS,
            True,
            "Read-only PostgreSQL connectivity probe completed.",
        )
    except Exception:
        return _result(
            "connectivity",
            PostgresRuntimeStatus.FAILED,
            False,
            "PostgreSQL connectivity probe failed; private details were suppressed.",
        )
    finally:
        if engine is not None and hasattr(engine, "dispose"):
            engine.dispose()


def _run_injected_status(
    settings: Settings,
    enabled: bool,
    operation: str,
    secret_provider: Any,
    runner: Callable[..., Any] | None,
) -> PostgresConnectivityCheckResult:
    _gate(settings, enabled, operation)
    if runner is None:
        return _result(
            operation,
            PostgresRuntimeStatus.DEPENDENCY_MISSING,
            False,
            "A private injected status adapter is required.",
        )
    _, database_url = _provider_and_url(settings, secret_provider)
    try:
        runner(database_url, settings)
    except Exception:
        return _result(
            operation,
            PostgresRuntimeStatus.FAILED,
            False,
            f"PostgreSQL {operation} check failed; private details were suppressed.",
        )
    return _result(
        operation,
        PostgresRuntimeStatus.SUCCESS,
        True,
        f"PostgreSQL {operation} check completed with sanitized output.",
    )


def run_postgres_migration_status_check(
    settings: Settings,
    secret_provider: Any = None,
    migration_runner: Callable[..., Any] | None = None,
) -> PostgresConnectivityCheckResult:
    if migration_runner is None:
        _gate(
            settings,
            settings.postgres_runtime_migrations_enabled,
            "migration_status",
        )
        if find_spec("psycopg") is None:
            return _result(
                "migration_status",
                PostgresRuntimeStatus.DEPENDENCY_MISSING,
                False,
                "Optional PostgreSQL driver is not installed.",
            )
        migration_runner = _default_migration_status_runner
    return _run_injected_status(
        settings,
        settings.postgres_runtime_migrations_enabled,
        "migration_status",
        secret_provider,
        migration_runner,
    )


def _default_migration_status_runner(database_url: str, settings: Settings) -> None:
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    engine = create_engine(
        database_url,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_timeout=settings.postgres_pool_timeout_seconds,
        pool_recycle=settings.postgres_pool_recycle_seconds,
        pool_pre_ping=settings.postgres_pool_pre_ping,
        connect_args={
            "connect_timeout": settings.postgres_runtime_timeout_seconds,
            "options": (
                "-c statement_timeout="
                f"{settings.postgres_runtime_statement_timeout_seconds * 1000}"
            ),
            **({"sslmode": "require"} if settings.postgres_require_ssl else {}),
        },
    )
    try:
        with engine.connect() as connection:
            MigrationContext.configure(connection).get_current_heads()
    finally:
        engine.dispose()


def run_postgres_backup_verification_check(
    settings: Settings,
    secret_provider: Any = None,
    verifier: Callable[..., Any] | None = None,
) -> PostgresConnectivityCheckResult:
    return _run_injected_status(
        settings,
        settings.postgres_runtime_backup_check_enabled,
        "backup_verification",
        secret_provider,
        verifier,
    )


def run_postgres_restore_drill_check(
    settings: Settings,
    secret_provider: Any = None,
    verifier: Callable[..., Any] | None = None,
) -> PostgresConnectivityCheckResult:
    return _run_injected_status(
        settings,
        settings.postgres_runtime_restore_check_enabled,
        "restore_drill",
        secret_provider,
        verifier,
    )
