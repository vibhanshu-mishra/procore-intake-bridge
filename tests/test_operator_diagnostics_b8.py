import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.main import app
from app.models.webhook_events import WebhookEvent
from app.services.diagnostic_redaction import (
    REDACTED,
    DiagnosticRedactionError,
    assert_diagnostics_safe,
    contains_sensitive_material,
    redact_diagnostic_value,
    redact_text,
)
from app.services.operator_diagnostics import (
    OperatorDiagnosticsBlockedError,
    build_operator_diagnostics_report,
)
from app.services.support_bundle import (
    EXPECTED_FILES,
    SupportBundleBlockedError,
    build_support_bundle,
    check_support_bundle_redaction,
)


def configured(**values):
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "unsafe",
    [
        "Authorization: Bearer fake-support-token",
        "webhook_secret=fake-secret-value",
        "postgresql://example:fake-password@db.invalid/app",
        "https://example.invalid/file?signature=fake-signature",
        "/Users/example/private/customer.json",
        "operator@example.invalid",
        "(312) 555-0199",
    ],
)
def test_strict_redaction_removes_sensitive_text(unsafe):
    redacted = redact_text(unsafe)
    assert REDACTED in redacted
    assert not contains_sensitive_material(redacted)


def test_nested_payloads_and_sensitive_keys_are_redacted():
    original = {
        "safe": "example-placeholder",
        "raw_payload": {"project_id": "987654", "name": "private"},
        "client_secret": "fake-secret-value",
        "nested": {"authorization": "Bearer fake-support-token"},
    }
    redacted = redact_diagnostic_value(original)
    assert redacted["safe"] == "example-placeholder"
    assert redacted["raw_payload"] == REDACTED
    assert redacted["client_secret"] == REDACTED
    assert redacted["nested"]["authorization"] == REDACTED
    assert_diagnostics_safe(redacted)
    with pytest.raises(DiagnosticRedactionError):
        assert_diagnostics_safe(original)


def test_diagnostics_without_database_is_safely_unavailable():
    report = build_operator_diagnostics_report(configured(), app=app)
    serialized = report.model_dump_json()
    assert report.external_calls is False
    assert report.procore_calls is False
    assert report.values_exposed is False
    assert report.database.available is False
    assert report.routes.total > 0
    assert "sqlite://" not in serialized
    assert "/Users/" not in serialized
    assert '"payload_json"' not in serialized


def test_database_and_queue_diagnostics_include_counts_only(db_session):
    db_session.add(WebhookEvent(
        event_id="example-diagnostic-event",
        event_type="rfi.created",
        resource_type="rfi",
        action="created",
        payload_json={"private": "must-not-appear"},
        normalized_json={"event_id": "must-not-appear"},
        processing_status="queued",
    ))
    db_session.commit()
    report = build_operator_diagnostics_report(configured(), db_session, app)
    assert report.database.table_counts["webhook_events"] == 1
    assert report.queue.pending == 1
    serialized = report.model_dump_json()
    assert "must-not-appear" not in serialized
    assert "payload_json" not in serialized


def test_unsafe_diagnostics_inclusion_settings_fail_closed():
    with pytest.raises(OperatorDiagnosticsBlockedError):
        build_operator_diagnostics_report(
            configured(support_bundle_include_raw_logs=True), app=app
        )
    with pytest.raises(OperatorDiagnosticsBlockedError):
        build_operator_diagnostics_report(
            configured(operator_diagnostics_include_env_key_names=True), app=app
        )


def test_non_sqlite_migration_diagnostics_do_not_connect(monkeypatch):
    def forbidden(_settings):
        raise AssertionError("external database inspection must not run")

    monkeypatch.setattr(
        "app.services.operator_diagnostics.build_migration_status_report",
        forbidden,
    )
    report = build_operator_diagnostics_report(
        configured(database_url="postgresql://db.invalid/app"), app=app
    )
    migration = next(section for section in report.sections if section.name == "migration_status")
    assert migration.status == "unavailable"
    assert migration.summary["external_connection"] is False


def test_support_bundle_contains_only_expected_sanitized_files(tmp_path):
    result = build_support_bundle(
        configured(), app=app, output_root=tmp_path / "support-output"
    )
    directory = tmp_path / "support-output" / result.output_directory
    assert {item.name for item in directory.iterdir()} == EXPECTED_FILES
    assert result.external_calls is False
    assert result.sensitive_values_included is False
    contents = "\n".join(item.read_text() for item in directory.iterdir())
    assert ".env" not in contents
    assert "/Users/" not in contents
    assert "Authorization:" not in contents
    assert '"payload_json"' not in contents
    assert not any(item.suffix in {".log", ".db", ".sqlite"} for item in directory.iterdir())
    assert check_support_bundle_redaction(directory).safe is True


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_support_bundle_path_traversal_is_blocked(root):
    with pytest.raises(SupportBundleBlockedError):
        build_support_bundle(configured(), app=app, output_root=root)


def test_redaction_checker_fails_on_unsafe_temp_file(tmp_path):
    unsafe = tmp_path / "unsafe.txt"
    unsafe.write_text("Authorization: Bearer fake-intentionally-unsafe-token")
    report = check_support_bundle_redaction(unsafe)
    assert report.safe is False
    assert report.issues_count > 0


def test_diagnostics_route_is_sanitized_and_writes_no_files(client, tmp_path, monkeypatch):
    monkeypatch.setenv(
        "PROCORE_INTAKE_SUPPORT_BUNDLE_OUTPUT_ROOT", str(tmp_path / "unused")
    )
    get_settings.cache_clear()
    response = client.get("/deployment/diagnostics")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.json()
    assert payload["external_calls"] is False
    assert payload["procore_calls"] is False
    assert payload["database"]["rows_included"] is False
    assert not (tmp_path / "unused").exists()
    get_settings.cache_clear()


def test_diagnostics_route_is_protected_by_operator_auth(client, monkeypatch):
    ref = "PROCORE_INTAKE_SECRET_B8_ADMIN_TEST"
    token = "fake-b8-route-token"
    monkeypatch.setenv("PROCORE_INTAKE_ADMIN_AUTH_MODE", "token_required")
    monkeypatch.setenv("PROCORE_INTAKE_ADMIN_TOKEN_SECRET_REF", ref)
    monkeypatch.setenv(ref, token)
    get_settings.cache_clear()
    assert client.get("/deployment/diagnostics").status_code == 401
    accepted = client.get(
        "/deployment/diagnostics",
        headers={"X-Procore-Intake-Admin-Token": token},
    )
    assert accepted.status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    get_settings.cache_clear()


def test_diagnostics_and_bundle_cli_work_without_absolute_output(tmp_path):
    diagnostics = subprocess.run(
        [sys.executable, "scripts/print_operator_diagnostics.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"external_calls": false' in diagnostics.stdout
    root = tmp_path / "bundle"
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_support_bundle.py",
            "--output-root",
            str(root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(tmp_path) not in generated.stdout
    checked = subprocess.run(
        [
            sys.executable,
            "scripts/check_support_bundle_redaction.py",
            str(root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"safe": true' in checked.stdout


def test_bundle_cli_rejects_traversal():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_support_bundle.py",
            "--output-root",
            "../unsafe-support-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unsafe" in result.stdout.casefold()


def test_no_external_observability_dependencies_or_raw_data_terms():
    dependencies = Path("pyproject.toml").read_text().casefold()
    forbidden = ("sentry", "datadog", "opentelemetry", "prometheus", "newrelic")
    assert not any(term in dependencies for term in forbidden)
