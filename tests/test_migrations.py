import json
import os
import subprocess
from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.config import Settings
from app.database import Base
from app.services.deployment_readiness import build_deployment_readiness_report
from app.services.migration_status import (
    build_migration_status_report,
    compare_metadata_to_migrated_schema,
    get_alembic_config,
    get_head_revision,
)
from scripts.audit_public_safety import audit_paths


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_migration_foundation_and_stable_initial_revision():
    initial = Path("migrations/versions/0001_initial_schema.py")
    assert Path("alembic.ini").is_file()
    assert Path("migrations/env.py").is_file()
    assert Path("migrations/script.py.mako").is_file()
    assert initial.is_file()
    content = initial.read_text()
    assert 'revision: str = "0001_initial_schema"' in content
    assert "op.create_table" in content
    assert "bulk_insert" not in content
    assert "PROCORE_INTAKE_SECRET_" not in content
    assert "postgresql://" not in Path("alembic.ini").read_text()


def test_upgrade_and_downgrade_use_temporary_sqlite_only(tmp_path):
    database = tmp_path / "migration-test.sqlite"
    configured = settings()
    config = get_alembic_config(configured, sqlite_url(database))
    command.upgrade(config, "head")
    engine = create_engine(sqlite_url(database))
    try:
        tables = set(inspect(engine).get_table_names())
        assert set(Base.metadata.tables) <= tables
        assert "alembic_version" in tables
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                == "0002_intake_lifecycle"
            )
    finally:
        engine.dispose()
    command.downgrade(config, "base")
    engine = create_engine(sqlite_url(database))
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()


def test_status_detects_pending_without_creating_database(tmp_path):
    database = tmp_path / "does-not-exist.sqlite"
    report = build_migration_status_report(
        settings(), database_url_override=sqlite_url(database)
    )
    assert report.head_revision == "0002_intake_lifecycle"
    assert report.current_revision is None
    assert report.pending_migration_detected is True
    assert report.database_url_summary == "sqlite local file"
    assert not database.exists()


def test_status_detects_head_and_schema_matches_metadata(tmp_path):
    database = tmp_path / "at-head.sqlite"
    configured = settings()
    command.upgrade(get_alembic_config(configured, sqlite_url(database)), "head")
    report = build_migration_status_report(
        configured, database_url_override=sqlite_url(database)
    )
    assert get_head_revision(configured) == "0002_intake_lifecycle"
    assert report.current_revision == report.head_revision
    assert report.is_at_head is True
    assert compare_metadata_to_migrated_schema(sqlite_url(database), configured) == []


def test_status_masks_external_database_credentials_without_connecting():
    secret = "fake-database-password"
    report = build_migration_status_report(
        settings(),
        database_url_override=f"postgresql://user:{secret}@db.invalid/app",
    )
    serialized = report.model_dump_json()
    assert secret not in serialized
    assert "***" in report.database_url_summary
    assert any(finding.severity == "error" for finding in report.findings)


def test_readiness_never_creates_or_migrates_database(tmp_path):
    database = tmp_path / "readiness.sqlite"
    report = build_deployment_readiness_report(
        settings(database_url=sqlite_url(database))
    )
    assert report.ready_for_local is True
    assert not database.exists()


def test_migration_route_is_read_only_and_sanitized(client):
    response = client.get("/deployment/migrations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["head_revision"] == "0002_intake_lifecycle"
    assert "password" not in response.text.casefold()
    assert "sqlite://" not in response.text


def test_migration_cli_scripts_pass_safely():
    for script in (
        "scripts/check_migration_status.py",
        "scripts/run_migration_safety_check.py",
        "scripts/verify_schema_drift.py",
    ):
        result = subprocess.run(
            [".venv/bin/python", script],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "postgresql://" not in result.stdout
        assert "client_secret" not in result.stdout


def test_strict_status_fails_on_pending_temp_database(tmp_path):
    database = tmp_path / "pending.sqlite"
    environment = os.environ.copy()
    environment.update(
        {
            "PROCORE_INTAKE_DATABASE_URL": sqlite_url(database),
            "PROCORE_INTAKE_MIGRATION_CHECK_ENABLED": "true",
        }
    )
    result = subprocess.run(
        [".venv/bin/python", "scripts/check_migration_status.py", "--strict"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode != 0
    assert not database.exists()
    assert "pending_migration" in result.stdout


def test_public_audit_rejects_database_files_and_credential_urls(tmp_path):
    database = tmp_path / "accidental.sqlite"
    database.write_bytes(b"SQLite format 3")
    config = tmp_path / "unsafe.txt"
    unsafe_password = "cred" + "ential-material"
    config.write_text(
        f"postgresql://operator:{unsafe_password}@db.invalid/app"
    )
    issues = audit_paths([database, config])
    serialized = json.dumps([issue.issue_type for issue in issues])
    assert "tracked local database file" in serialized
    assert "database URL contains credentials" in serialized
