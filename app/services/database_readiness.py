import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import Settings
from app.schemas.database import (
    DatabaseArtifactResult,
    DatabaseBackupPlan,
    DatabaseConnectionPlan,
    DatabaseFinding,
    DatabaseMigrationPlan,
    DatabaseProviderKind,
    DatabaseProviderStatus,
    DatabaseReadinessReport,
    DatabaseRestorePlan,
    DatabaseUrlSource,
)

DATABASE_URL = re.compile(
    r"(?i)\b(?:postgres(?:ql)?(?:\+\w+)?|sqlite(?:\+\w+)?|mysql|mariadb|mongodb)://\S+"
)
PASSWORD_VALUE = re.compile(r"(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+")
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
SAFE_REF = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


class DatabaseReadinessError(RuntimeError):
    """Database readiness failed without exposing private configuration."""


class DatabaseReadinessBlockedError(DatabaseReadinessError):
    pass


def sanitize_database_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): sanitize_database_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_database_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        result = DATABASE_URL.sub("[masked-database-url]", value)
        result = PASSWORD_VALUE.sub("[masked-credential]", result)
        if ABSOLUTE_PATH.search(result):
            return "[masked-path]"
        return result
    return value


def mask_database_url(value: str) -> str:
    if not value:
        return "[database-not-configured]"
    if DATABASE_URL.search(value):
        try:
            scheme = urlsplit(value).scheme.casefold()
        except ValueError:
            scheme = "database"
        provider = "postgres" if scheme.startswith("postgres") else "sqlite"
        return f"{provider}://***:***@[masked]/[masked]"
    if SAFE_REF.fullmatch(value):
        return f"database-ref-{value[-4:].casefold()}"
    return "[masked-database-reference]"


def validate_database_url_ref(ref: str, settings: Settings) -> str:
    del settings
    value = ref.strip()
    if DATABASE_URL.search(value) or PASSWORD_VALUE.search(value):
        raise DatabaseReadinessBlockedError(
            "Database URL reference contains inline private configuration."
        )
    if not SAFE_REF.fullmatch(value):
        raise DatabaseReadinessBlockedError("Database URL reference is invalid.")
    return value


def classify_database_provider(
    value_or_ref: str, settings: Settings
) -> DatabaseProviderKind:
    value = value_or_ref.strip().casefold()
    if value.startswith(("postgresql://", "postgres://", "postgresql+")):
        return DatabaseProviderKind.POSTGRES
    if value.startswith(("sqlite://", "sqlite+")):
        return DatabaseProviderKind.SQLITE
    return DatabaseProviderKind(settings.database_provider)


def _mode(settings: Settings, selected_mode: str | None) -> str:
    value = selected_mode or settings.usage_mode
    return value if value in {"demo", "sandbox", "pilot"} else "demo"


def build_database_readiness_report(
    settings: Settings, selected_mode: str | None = None
) -> DatabaseReadinessReport:
    mode = _mode(settings, selected_mode)
    provider = DatabaseProviderKind(settings.database_provider)
    findings: list[DatabaseFinding] = []
    blocking = False
    if provider == DatabaseProviderKind.SQLITE:
        if not settings.database_allow_sqlite:
            blocking = True
            findings.append(DatabaseFinding(
                code="sqlite_disabled", severity="blocking",
                message="SQLite is disabled by database provider policy.",
            ))
        elif mode == "pilot" and settings.postgres_required_for_pilot:
            blocking = True
            findings.append(DatabaseFinding(
                code="postgres_required_for_pilot", severity="blocking",
                message="Pilot mode requires privately configured PostgreSQL.",
            ))
        elif mode == "sandbox":
            findings.append(DatabaseFinding(
                code="postgres_recommended", severity="warning",
                message=(
                    "SQLite is suitable for local simulation; hosted Sandbox should "
                    "use PostgreSQL."
                ),
            ))
        else:
            findings.append(DatabaseFinding(
                code="sqlite_demo", severity="info",
                message="SQLite is available for local Demo mode.",
            ))
    else:
        if not settings.database_allow_postgres:
            blocking = True
            findings.append(DatabaseFinding(
                code="postgres_disabled", severity="blocking",
                message="PostgreSQL is disabled by database provider policy.",
            ))
        try:
            validate_database_url_ref(settings.database_url_ref, settings)
        except DatabaseReadinessBlockedError:
            blocking = True
            findings.append(DatabaseFinding(
                code="database_url_ref", severity="blocking",
                message="PostgreSQL requires a valid private database URL reference.",
            ))
        if settings.postgres_require_ssl:
            findings.append(DatabaseFinding(
                code="postgres_ssl", severity="warning",
                message="Private PostgreSQL configuration must enforce SSL.",
            ))
        findings.append(DatabaseFinding(
            code="connectivity_not_attempted", severity="info",
            message="No external database connectivity was attempted.",
        ))
    migration_ready = (
        settings.migration_check_enabled
        and settings.migration_execution_plan_required
        and not settings.auto_run_migrations
    )
    backup_ready = provider == DatabaseProviderKind.SQLITE or (
        mode != "pilot" or settings.postgres_require_backup_plan
    )
    rollback_ready = provider == DatabaseProviderKind.SQLITE or (
        mode != "pilot" or settings.postgres_require_rollback_plan
    )
    if not migration_ready:
        blocking = mode == "pilot"
        findings.append(DatabaseFinding(
            code="migration_plan", severity="blocking" if mode == "pilot" else "warning",
            message="A reviewed migration execution plan is required.",
        ))
    status = (
        DatabaseProviderStatus.BLOCKED
        if blocking
        else DatabaseProviderStatus.READY
    )
    return DatabaseReadinessReport(
        provider=provider,
        selected_mode=mode,
        status=status,
        sqlite_allowed=settings.database_allow_sqlite,
        postgres_allowed=settings.database_allow_postgres,
        external_connect_enabled=settings.database_external_connect_enabled,
        migration_execution_ready=migration_ready,
        backup_plan_ready=backup_ready,
        rollback_plan_ready=rollback_ready,
        findings=findings,
        recommended_next_steps=[
            "Keep database configuration in the selected private secret provider.",
            "Review migration, backup, restore, and rollback plans before Pilot use.",
        ],
    )


def build_database_connection_plan(
    settings: Settings, selected_mode: str | None = None
) -> DatabaseConnectionPlan:
    provider = DatabaseProviderKind(settings.database_provider)
    ref = (
        validate_database_url_ref(settings.database_url_ref, settings)
        if provider == DatabaseProviderKind.POSTGRES
        else "SQLITE_LOCAL_REFERENCE"
    )
    return DatabaseConnectionPlan(
        provider=provider,
        selected_mode=_mode(settings, selected_mode),
        masked_url_ref=mask_database_url(ref),
        url_source=DatabaseUrlSource(settings.database_url_source),
        external_connect_enabled=settings.database_external_connect_enabled,
        steps=[
            "Resolve the URL only inside the explicitly gated connectivity process.",
            "Use a bounded connection timeout and a read-only SELECT 1 probe.",
            "Suppress provider exceptions and dispose the connection.",
        ],
    )


def build_migration_execution_plan(
    settings: Settings, selected_mode: str | None = None
) -> DatabaseMigrationPlan:
    from app.services.migration_status import get_head_revision

    provider = DatabaseProviderKind(settings.database_provider)
    try:
        head_known = bool(get_head_revision(settings))
    except Exception:
        head_known = False
    return DatabaseMigrationPlan(
        provider=provider,
        selected_mode=_mode(settings, selected_mode),
        execution_ready=(
            head_known
            and settings.migration_execution_plan_required
            and not settings.auto_run_migrations
        ),
        steps=[
            "Confirm a reviewed maintenance window and responsible operator.",
            "Verify a current backup and tested restore procedure.",
            "Compare current revision with the repository Alembic head.",
            "Run the approved Alembic command manually against private configuration.",
            "Verify application health and migration head; invoke rollback plan if needed.",
        ],
        command_placeholders=[
            "DATABASE_URL_REF_PLACEHOLDER alembic current",
            "DATABASE_URL_REF_PLACEHOLDER alembic upgrade head",
        ],
    )


def build_backup_restore_plan(
    settings: Settings, selected_mode: str | None = None
) -> tuple[DatabaseBackupPlan, DatabaseRestorePlan]:
    del selected_mode
    provider = DatabaseProviderKind(settings.database_provider)
    ready = provider == DatabaseProviderKind.SQLITE or (
        settings.postgres_require_backup_plan
        and settings.postgres_require_rollback_plan
    )
    backup = DatabaseBackupPlan(
        provider=provider,
        ready=ready,
        steps=[
            "Identify the approved private backup service and retention policy.",
            "Create a backup under operator control and record only a masked evidence reference.",
            "Verify backup completion without copying dump contents into reports.",
        ],
    )
    restore = DatabaseRestorePlan(
        provider=provider,
        ready=ready,
        steps=[
            "Restore into an isolated approved environment.",
            "Verify migration revision and application health.",
            "Record sanitized evidence and rollback decision privately.",
        ],
    )
    return backup, restore


def render_database_readiness_markdown(report: DatabaseReadinessReport) -> str:
    return (
        "# Database readiness\n\n"
        f"- Provider: `{report.provider}`\n"
        f"- Mode: `{report.selected_mode}`\n"
        f"- Status: `{report.status}`\n"
        "- External connectivity attempted: `false`\n"
        "- Database URL, credentials, and hostnames exposed: `false`\n"
    )


def render_migration_execution_plan_markdown(plan: DatabaseMigrationPlan) -> str:
    lines = ["# Migration execution plan", "", "This plan executes nothing.", ""]
    lines.extend(f"{index}. {step}" for index, step in enumerate(plan.steps, 1))
    return "\n".join(lines) + "\n"


def render_backup_restore_plan_markdown(
    plan: DatabaseBackupPlan | DatabaseRestorePlan,
) -> str:
    lines = ["# Backup and restore plan", "", "No backup or dump was read.", ""]
    lines.extend(f"- {step}" for step in plan.steps)
    return "\n".join(lines) + "\n"


def validate_database_report_safe(report: Any) -> None:
    raw = (
        report.model_dump(mode="json")
        if hasattr(report, "model_dump")
        else report
    )
    text = json.dumps(raw)
    if DATABASE_URL.search(text) or PASSWORD_VALUE.search(text) or ABSOLUTE_PATH.search(text):
        raise DatabaseReadinessBlockedError("Database report failed redaction validation.")


def write_database_readiness_artifacts(
    report: DatabaseReadinessReport, output_root: Path
) -> DatabaseArtifactResult:
    if output_root.is_absolute() or output_root.parts[:1] not in {
        ("migration-output",), ("database-output",), ("db-output",)
    }:
        raise DatabaseReadinessBlockedError("Database output root is unsafe.")
    validate_database_report_safe(report)
    output_root.mkdir(parents=True, exist_ok=True)
    files = ["database-readiness.db-report.json", "database-readiness.db-report.md"]
    (output_root / files[0]).write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n"
    )
    (output_root / files[1]).write_text(render_database_readiness_markdown(report))
    return DatabaseArtifactResult(files=files, written=True)
