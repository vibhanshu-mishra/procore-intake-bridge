from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect

from app.config import Settings
from app.database import Base
from app.services.database_readiness import mask_database_url as _mask_database_url


class MigrationStatusError(RuntimeError):
    """A sanitized migration inspection error."""


class MigrationFinding(BaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str


class MigrationStatus(BaseModel):
    migration_check_enabled: bool
    script_location: str
    current_revision: str | None
    head_revision: str | None
    is_at_head: bool
    pending_migrations_count: int
    pending_migration_detected: bool
    database_url_summary: str
    findings: list[MigrationFinding] = Field(default_factory=list)
    generated_at: datetime


def get_alembic_config(
    settings: Settings, database_url_override: str | None = None
) -> Config:
    config = Config("alembic.ini")
    config.set_main_option(
        "script_location", str(settings.migration_script_location)
    )
    database_url = database_url_override or settings.database_url
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def mask_database_url(url: str) -> str:
    return _mask_database_url(url)


def _sqlite_file_path(database_url: str) -> Path | None:
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"sqlite", "sqlite+pysqlite"}:
        raise MigrationStatusError(
            "B3 migration inspection supports local SQLite only."
        )
    if parsed.path in {"", "/", "/:memory:"}:
        return None
    prefix = f"{parsed.scheme}:///"
    raw_path = unquote(database_url.split("?", 1)[0][len(prefix) :])
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _database_summary(database_url: str) -> str:
    try:
        path = _sqlite_file_path(database_url)
    except MigrationStatusError:
        return mask_database_url(database_url)
    return "sqlite memory" if path is None else "sqlite local file"


def get_current_revision(database_url: str, settings: Settings) -> str | None:
    del settings
    path = _sqlite_file_path(database_url)
    if path is not None and not path.exists():
        return None
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    except Exception as exc:
        raise MigrationStatusError(
            "Current migration revision could not be inspected."
        ) from exc
    finally:
        engine.dispose()


def get_head_revision(settings: Settings) -> str | None:
    try:
        return ScriptDirectory.from_config(
            get_alembic_config(settings)
        ).get_current_head()
    except Exception as exc:
        raise MigrationStatusError(
            "Migration head could not be inspected."
        ) from exc


def build_migration_status_report(
    settings: Settings, database_url_override: str | None = None
) -> MigrationStatus:
    database_url = database_url_override or settings.database_url
    findings: list[MigrationFinding] = []
    if not settings.migration_check_enabled:
        return MigrationStatus(
            migration_check_enabled=False,
            script_location=settings.migration_script_location.name,
            current_revision=None,
            head_revision=None,
            is_at_head=False,
            pending_migrations_count=0,
            pending_migration_detected=False,
            database_url_summary=_database_summary(database_url),
            findings=[
                MigrationFinding(
                    severity="warning",
                    code="migration_check_disabled",
                    message="Migration status checks are disabled.",
                )
            ],
            generated_at=datetime.now(UTC),
        )
    try:
        head = get_head_revision(settings)
        current = get_current_revision(database_url, settings)
        script = ScriptDirectory.from_config(get_alembic_config(settings, database_url))
        pending = (
            len(list(script.iterate_revisions(head, current)))
            if head is not None and current != head
            else 0
        )
        if pending:
            findings.append(
                MigrationFinding(
                    severity="warning",
                    code="pending_migrations",
                    message="The database is not at the repository migration head.",
                )
            )
        else:
            findings.append(
                MigrationFinding(
                    severity="info",
                    code="migration_at_head",
                    message="The inspected database is at migration head.",
                )
            )
        return MigrationStatus(
            migration_check_enabled=True,
            script_location=settings.migration_script_location.name,
            current_revision=current,
            head_revision=head,
            is_at_head=current == head and head is not None,
            pending_migrations_count=pending,
            pending_migration_detected=pending > 0,
            database_url_summary=_database_summary(database_url),
            findings=findings,
            generated_at=datetime.now(UTC),
        )
    except MigrationStatusError as exc:
        return MigrationStatus(
            migration_check_enabled=True,
            script_location=settings.migration_script_location.name,
            current_revision=None,
            head_revision=None,
            is_at_head=False,
            pending_migrations_count=0,
            pending_migration_detected=False,
            database_url_summary=_database_summary(database_url),
            findings=[
                MigrationFinding(
                    severity="error",
                    code="migration_status_error",
                    message=str(exc),
                )
            ],
            generated_at=datetime.now(UTC),
        )


def compare_metadata_to_migrated_schema(
    database_url: str, settings: Settings
) -> list[MigrationFinding]:
    del settings
    _sqlite_file_path(database_url)
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
        expected_tables = set(Base.metadata.tables)
        findings: list[MigrationFinding] = []
        for table in sorted(expected_tables - actual_tables):
            findings.append(
                MigrationFinding(
                    severity="error",
                    code="missing_table",
                    message=f"Metadata table is missing from migration schema: {table}.",
                )
            )
        for table in sorted(actual_tables - expected_tables):
            findings.append(
                MigrationFinding(
                    severity="error",
                    code="extra_table",
                    message=f"Migration schema has an extra table: {table}.",
                )
            )
        for table in sorted(expected_tables & actual_tables):
            expected_columns = set(Base.metadata.tables[table].columns.keys())
            actual_columns = {
                column["name"] for column in inspector.get_columns(table)
            }
            for column in sorted(expected_columns - actual_columns):
                findings.append(
                    MigrationFinding(
                        severity="error",
                        code="missing_column",
                        message=f"Migration schema is missing {table}.{column}.",
                    )
                )
            for column in sorted(actual_columns - expected_columns):
                findings.append(
                    MigrationFinding(
                        severity="error",
                        code="extra_column",
                        message=f"Migration schema has extra {table}.{column}.",
                    )
                )
        return findings
    except Exception as exc:
        raise MigrationStatusError(
            "Schema drift inspection failed safely."
        ) from exc
    finally:
        engine.dispose()
