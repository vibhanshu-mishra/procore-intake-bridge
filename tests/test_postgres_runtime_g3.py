import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.database_runtime import PostgresRuntimeStatus
from app.services.database_runtime import (
    POSTGRES_RUNTIME_CONFIRMATION_PHRASE,
    DatabaseRuntimeBlockedError,
    build_postgres_backup_verification_plan,
    build_postgres_migration_execution_plan,
    build_postgres_restore_drill_plan,
    build_postgres_runtime_report,
    run_postgres_connectivity_check,
    run_postgres_migration_status_check,
    validate_postgres_runtime_report_safe,
)

ROOT = Path(__file__).resolve().parents[1]
OFFLINE_SCRIPTS = (
    "check_postgres_runtime.py",
    "print_postgres_runtime_template.py",
    "plan_postgres_migration_run.py",
    "plan_postgres_backup_restore_drill.py",
)
LIVE_SCRIPTS = (
    "run_postgres_connectivity_check.py",
    "run_postgres_migration_status_check.py",
)
FORBIDDEN_OUTPUT = (
    "postgresql://",
    "password=",
    "select 1",
    "/users/",
    "/private/",
    ".dump",
    ".backup",
)


class FakeSecrets:
    def get_secret(self, ref: str) -> str:
        assert ref == "DATABASE_URL"
        return "postgresql://test-placeholder:test-placeholder@placeholder.invalid/test-placeholder"


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, statement):
        del statement
        return object()


class FakeEngine:
    def __init__(self):
        self.disposed = False

    def connect(self):
        return FakeConnection()

    def dispose(self):
        self.disposed = True


def runtime_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "database_provider": "postgres",
        "database_url_ref": "DATABASE_URL",
        "postgres_runtime_enabled": True,
        "postgres_runtime_confirmation": POSTGRES_RUNTIME_CONFIRMATION_PHRASE,
        "postgres_runtime_connectivity_enabled": True,
        "postgres_runtime_migrations_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_defaults_are_offline_and_need_configuration():
    report = build_postgres_runtime_report(Settings(_env_file=None))
    assert report.status == PostgresRuntimeStatus.NEEDS_CONFIGURATION
    assert report.runtime_enabled is False
    assert report.cloud_or_external_db_contact_attempted is False
    assert report.pool_config_summary.sensitive_fields_included is False
    validate_postgres_runtime_report_safe(report)


def test_offline_plans_execute_and_inspect_nothing():
    settings = Settings(_env_file=None)
    migration = build_postgres_migration_execution_plan(settings)
    backup = build_postgres_backup_verification_plan(settings)
    restore = build_postgres_restore_drill_plan(settings)
    assert migration.migration_executed is False
    assert migration.external_contact_attempted is False
    assert backup.backup_files_inspected is False
    assert backup.backup_executed is False
    assert restore.dump_or_backup_contents_inspected is False
    assert restore.restore_executed is False


def test_connectivity_refuses_without_enablement_or_confirmation():
    with pytest.raises(DatabaseRuntimeBlockedError, match="runtime disabled"):
        run_postgres_connectivity_check(
            Settings(_env_file=None, database_provider="postgres")
        )
    with pytest.raises(DatabaseRuntimeBlockedError, match="confirmation missing"):
        run_postgres_connectivity_check(
            runtime_settings(postgres_runtime_confirmation="")
        )


def test_fake_connectivity_success_is_sanitized():
    engine = FakeEngine()
    captured = {}

    def factory(url, **kwargs):
        captured["url_received"] = bool(url)
        captured["pool_size"] = kwargs["pool_size"]
        return engine

    result = run_postgres_connectivity_check(
        runtime_settings(), FakeSecrets(), factory
    )
    assert result.success is True
    assert result.status == PostgresRuntimeStatus.SUCCESS
    assert result.cloud_or_external_db_contact_attempted is True
    assert captured == {"url_received": True, "pool_size": 5}
    assert engine.disposed is True
    assert not any(term in json.dumps(result.model_dump()).casefold() for term in FORBIDDEN_OUTPUT)


def test_fake_connectivity_failure_suppresses_private_error():
    def factory(url, **kwargs):
        del url, kwargs
        raise RuntimeError(
            "postgresql://must-not-appear:must-not-appear@must-not-appear/must-not-appear"
        )

    result = run_postgres_connectivity_check(
        runtime_settings(), FakeSecrets(), factory
    )
    assert result.status == PostgresRuntimeStatus.FAILED
    assert result.success is False
    assert "must-not-appear" not in result.message


def test_migration_status_gates_and_fake_runner():
    with pytest.raises(DatabaseRuntimeBlockedError):
        run_postgres_migration_status_check(Settings(_env_file=None))
    called = []

    def runner(url, settings):
        called.append(bool(url) and settings.database_provider)

    result = run_postgres_migration_status_check(
        runtime_settings(), FakeSecrets(), runner
    )
    assert called == ["postgres"]
    assert result.success is True
    assert result.operation == "migration_status"
    assert result.migration_executed is False


@pytest.mark.parametrize("script", OFFLINE_SCRIPTS)
def test_offline_cli_runs_without_private_output(script):
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = (result.stdout + result.stderr).casefold()
    assert not any(term in output for term in FORBIDDEN_OUTPUT)


@pytest.mark.parametrize("script", LIVE_SCRIPTS)
def test_live_cli_refuses_by_default(script):
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    output = (result.stdout + result.stderr).casefold()
    assert "refused" in output
    assert not any(term in output for term in FORBIDDEN_OUTPUT)


def test_makefile_keeps_live_targets_out_of_quality():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "postgres-runtime-template",
        "postgres-runtime-check",
        "postgres-migration-plan",
        "postgres-backup-restore-plan",
    ):
        assert target in quality
    assert "postgres-connectivity-check" not in quality
    assert "postgres-migration-status-check" not in quality


def test_g3_docs_examples_and_navigation_are_public_safe():
    docs = (
        "postgres-runtime-operations.md",
        "postgres-connection-pooling.md",
        "postgres-migration-runbook.md",
        "postgres-backup-restore-drills.md",
    )
    for name in docs:
        assert (ROOT / "docs" / name).is_file()
        assert name in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    examples = list((ROOT / "examples/postgres-runtime").glob("*"))
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in examples if path.is_file()
    ).casefold()
    assert "placeholder" in combined
    assert not any(term in combined for term in FORBIDDEN_OUTPUT)
