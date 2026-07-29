import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.services.database_readiness import (
    DatabaseReadinessBlockedError,
    build_backup_restore_plan,
    build_database_connection_plan,
    build_database_readiness_report,
    build_migration_execution_plan,
    mask_database_url,
    render_backup_restore_plan_markdown,
    render_migration_execution_plan_markdown,
    sanitize_database_value,
    validate_database_report_safe,
    validate_database_url_ref,
)
from app.services.private_workspace import write_private_workspace
from scripts.check_database_connectivity import CONFIRMATION, run_connectivity_check

ROOT = Path(__file__).resolve().parents[1]


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_database_url_masking_never_exposes_components() -> None:
    raw = "postgresql://fake_user:fake_password@database.invalid/app"
    masked = mask_database_url(raw)
    assert masked.startswith("postgres://")
    assert "[masked]" in masked
    assert "fake_user" not in masked
    assert "fake_password" not in masked
    assert "database.invalid" not in masked
    assert sanitize_database_value({"database": raw}) == {
        "database": "[masked-database-url]"
    }


def test_database_ref_validation_blocks_inline_values() -> None:
    assert validate_database_url_ref("DATABASE_URL", configured()) == "DATABASE_URL"
    for value in (
        "postgresql://fake_user:fake_password@database.invalid/app",
        "password=fake-value",
        "not a ref",
    ):
        with pytest.raises(DatabaseReadinessBlockedError):
            validate_database_url_ref(value, configured())


def test_demo_accepts_sqlite_and_never_connects() -> None:
    report = build_database_readiness_report(configured(), "demo")
    assert report.provider == "sqlite"
    assert report.status == "ready"
    assert report.connectivity_attempted is False
    assert report.external_calls is False


def test_pilot_blocks_sqlite_when_postgres_required() -> None:
    report = build_database_readiness_report(configured(), "pilot")
    assert report.status == "blocked"
    assert "postgres_required_for_pilot" in {item.code for item in report.findings}


def test_postgres_readiness_is_masked_and_requires_ssl_posture() -> None:
    marker = "fake-database.invalid"
    settings = configured(
        database_provider="postgres",
        database_url_ref="DATABASE_URL",
        database_url=f"postgresql://fake_user:fake_password@{marker}/app",
    )
    report = build_database_readiness_report(settings, "pilot")
    serialized = report.model_dump_json()
    assert marker not in serialized
    assert "password" not in serialized
    assert "postgres_ssl" in {item.code for item in report.findings}
    assert report.connectivity_attempted is False
    validate_database_report_safe(report)


def test_connection_and_migration_plans_are_declarative() -> None:
    settings = configured(database_provider="postgres")
    connection = build_database_connection_plan(settings, "pilot")
    migration = build_migration_execution_plan(settings, "pilot")
    rendered = render_migration_execution_plan_markdown(migration)
    assert connection.connectivity_attempted is False
    assert migration.migration_executed is False
    assert "alembic upgrade head" not in rendered.casefold()
    assert "executes nothing" in rendered.casefold()


def test_backup_restore_plans_read_nothing() -> None:
    backup, restore = build_backup_restore_plan(
        configured(database_provider="postgres"), "pilot"
    )
    rendered = (
        render_backup_restore_plan_markdown(backup)
        + render_backup_restore_plan_markdown(restore)
    )
    assert backup.backup_files_read is False
    assert restore.dump_contents_read is False
    assert "No backup or dump was read" in rendered


def test_connectivity_refuses_without_both_gates() -> None:
    assert not run_connectivity_check(configured()).connectivity_attempted
    wrong = configured(
        database_external_connect_enabled=True,
        database_external_connect_confirmation="wrong",
    )
    assert not run_connectivity_check(wrong).connectivity_attempted


def test_mocked_connectivity_runs_select_one_and_sanitizes(monkeypatch) -> None:
    class Result:
        @staticmethod
        def scalar():
            return 1

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        @staticmethod
        def execute(statement):
            assert str(statement) == "SELECT 1"
            return Result()

    class Engine:
        @staticmethod
        def connect():
            return Connection()

        @staticmethod
        def dispose():
            return None

    class Provider:
        @staticmethod
        def get_secret(ref):
            assert ref == "DATABASE_URL"
            return "postgresql://fake_user:fake_password@database.invalid/app"

    monkeypatch.setattr(
        "scripts.check_database_connectivity.build_secret_provider",
        lambda settings: Provider(),
    )
    result = run_connectivity_check(
        configured(
            database_external_connect_enabled=True,
            database_external_connect_confirmation=CONFIRMATION,
        ),
        engine_factory=lambda *args, **kwargs: Engine(),
    )
    assert result.success
    assert result.connectivity_attempted
    assert "database.invalid" not in result.model_dump_json()


def test_private_workspace_generates_database_placeholders(tmp_path: Path) -> None:
    root = tmp_path / "private-workspace"
    result = write_private_workspace("sandbox_and_pilot", root)
    expected = {
        "database/README.private.md",
        "database/database-refs.private.env",
        "database/postgres-plan.private.md",
        "database/migration-execution-plan.private.md",
        "database/backup-plan.private.md",
        "database/restore-plan.private.md",
        "database/rollback-plan.private.md",
    }
    assert expected.issubset(result.files)
    contents = "\n".join(
        path.read_text() for path in root.rglob("*") if path.is_file()
    )
    assert "ENV_REF_PLACEHOLDER_DATABASE_URL" in contents
    assert "postgresql://" not in contents
    assert "password=" not in contents.casefold()


@pytest.mark.parametrize(
    "script",
    [
        "print_database_template.py",
        "check_database_readiness.py",
        "plan_migration_execution.py",
        "plan_backup_restore.py",
    ],
)
def test_offline_database_clis_are_safe(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "postgresql://" not in result.stdout
    assert "/Users/" not in result.stdout


def test_docs_make_and_gitignore_contract() -> None:
    for name in (
        "database-providers.md",
        "postgres-readiness.md",
        "migration-execution-plan.md",
        "backup-restore-plan.md",
    ):
        assert (ROOT / "docs" / name).is_file()
    makefile = (ROOT / "Makefile").read_text()
    assert "database-connectivity-check:" in makefile
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert "database-connectivity-check" not in quality
    ignored = (ROOT / ".gitignore").read_text()
    for item in ("migration-output/", "*.sql", "*.pgdump"):
        assert item in ignored
