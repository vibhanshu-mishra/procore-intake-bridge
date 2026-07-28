import json
import subprocess

import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.models import (
    AttachmentObject,
    IntakeRecord,
    OnboardingPacket,
    WebhookEvent,
)
from app.models.connections import DMSAConnection, ProcoreEnvironment
from app.services.sandbox_smoke import (
    SandboxSmokeBlockedError,
    build_sandbox_smoke_plan,
    run_sandbox_dmsa_smoke,
    sanitize_smoke_value,
    validate_sandbox_smoke_gates,
    write_sandbox_smoke_report,
)
from scripts.audit_public_safety import audit_paths

CONFIRMATION = "I_UNDERSTAND_THIS_IS_READ_ONLY_SANDBOX_ONLY"


def smoke_settings(**overrides) -> Settings:
    values = {
        "sandbox_smoke_enabled": True,
        "procore_live_mode_enabled": True,
        "procore_environment": "sandbox",
        "sandbox_smoke_attachment_downloads": False,
        "sandbox_smoke_max_records": 3,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def transient_connection(**overrides) -> DMSAConnection:
    values = {
        "id": 42,
        "name": "Fake sandbox",
        "procore_company_id": "company-test",
        "environment": ProcoreEnvironment.SANDBOX,
        "permitted_project_ids": ["project-1001"],
        "enabled_tools": ["rfis", "submittals"],
        "client_id_ref": "demo/client-id-placeholder",
        "secret_name": "demo/client-secret-placeholder",
    }
    values.update(overrides)
    return DMSAConnection(**values)


@pytest.mark.parametrize(
    "settings, confirmation, connection, project_id, company_id",
    [
        (
            Settings(_env_file=None),
            CONFIRMATION,
            transient_connection(),
            "project-1001",
            "company-test",
        ),
        (
            smoke_settings(),
            "incorrect",
            transient_connection(),
            "project-1001",
            "company-test",
        ),
        (
            smoke_settings(environment="production"),
            CONFIRMATION,
            transient_connection(),
            "project-1001",
            "company-test",
        ),
        (
            smoke_settings(sandbox_smoke_attachment_downloads=True),
            CONFIRMATION,
            transient_connection(),
            "project-1001",
            "company-test",
        ),
        (
            smoke_settings(sandbox_smoke_max_records=11),
            CONFIRMATION,
            transient_connection(),
            "project-1001",
            "company-test",
        ),
        (smoke_settings(), CONFIRMATION, transient_connection(), None, None),
        (smoke_settings(), CONFIRMATION, None, "project-1001", "company-test"),
        (
            smoke_settings(),
            CONFIRMATION,
            transient_connection(client_id_ref=None, secret_name=""),
            "project-1001",
            "company-test",
        ),
    ],
)
def test_smoke_gates_fail_closed(
    settings, confirmation, connection, project_id, company_id
):
    with pytest.raises(SandboxSmokeBlockedError):
        validate_sandbox_smoke_gates(
            settings, confirmation, connection, project_id, company_id
        )


def test_plan_is_safe_and_never_builds_live_probe(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("plan must not construct a Procore client")

    monkeypatch.setattr(
        "app.services.sandbox_smoke.build_pyprocore_client_for_connection",
        forbidden,
    )
    serialized = build_sandbox_smoke_plan(
        Settings(_env_file=None),
        connection_id=1,
        project_id="project-1001",
        company_id="company-test",
    ).model_dump_json()
    assert "read-only" in serialized
    assert '"procore_writes":false' in serialized
    assert '"attachment_downloads":false' in serialized
    assert "client-secret-placeholder" not in serialized


def test_sanitizer_redacts_sensitive_values_and_hashes_urls():
    raw_url = "https://sandbox.example.invalid/file?signature=fake-sensitive"
    private_path = "/private/example/smoke-output/report.json"
    sanitized = sanitize_smoke_value(
        {
            "access_token": "fake-sensitive",
            "client_secret": "fake-sensitive",
            "header": "Authorization: Bearer fake-sensitive",
            "signed_url": raw_url,
            "raw_payload": {"private": "data"},
            "path": private_path,
        }
    )
    serialized = json.dumps(sanitized)
    assert "fake-sensitive" not in serialized
    assert raw_url not in serialized
    assert private_path not in serialized
    assert "private" not in serialized
    assert "url_sha256:" in serialized


class MockProbe:
    def __init__(self, *_args):
        self.calls: list[str] = []

    def authenticate(self):
        self.calls.append("authenticate")
        return True

    def project_access(self):
        self.calls.append("project_access")
        return True

    def list_rfis(self, limit):
        self.calls.append("rfis")
        return [
            {
                "id": "fake-rfi-1",
                "status": "open",
                "attachments": [
                    {
                        "id": "fake-attachment",
                        "signed_url": "https://sandbox.invalid/file?signature=fake",
                    }
                ],
            }
        ][:limit]

    def list_submittals(self, limit):
        self.calls.append("submittals")
        return [{"id": "fake-submittal-1", "status": "pending"}][:limit]


def test_mock_live_smoke_is_sanitized_and_does_not_persist(db_session, connection, tmp_path):
    connection.environment = ProcoreEnvironment.SANDBOX
    connection.client_id_ref = "demo/client-id-placeholder"
    settings = smoke_settings()
    model_types = (IntakeRecord, AttachmentObject, WebhookEvent, OnboardingPacket)
    before = {
        model: db_session.scalar(select(func.count()).select_from(model))
        for model in model_types
    }
    report = run_sandbox_dmsa_smoke(
        settings,
        connection,
        CONFIRMATION,
        "project-1001",
        "company-test",
        probe_factory=MockProbe,
    )
    assert all(step.status == "passed" for step in report.steps)
    serialized = report.model_dump_json()
    assert "signature=fake" not in serialized
    assert "fake-rfi-1" not in serialized
    report_path = write_sandbox_smoke_report(report, tmp_path)
    assert report_path.name.endswith(".smoke.json")
    assert "signature=fake" not in report_path.read_text()
    after = {
        model: db_session.scalar(select(func.count()).select_from(model))
        for model in model_types
    }
    assert after == before


class FailingProbe(MockProbe):
    def authenticate(self):
        raise RuntimeError(
            "client_secret=fake-sensitive Authorization: Bearer fake-sensitive"
        )


def test_mock_failure_omits_sensitive_exception(connection):
    connection.environment = ProcoreEnvironment.SANDBOX
    connection.client_id_ref = "demo/client-id-placeholder"
    report = run_sandbox_dmsa_smoke(
        smoke_settings(),
        connection,
        CONFIRMATION,
        "project-1001",
        "company-test",
        probe_factory=FailingProbe,
    )
    serialized = report.model_dump_json()
    assert "fake-sensitive" not in serialized
    assert any(step.status == "failed" for step in report.steps)


def test_plan_cli_runs_without_credentials():
    result = subprocess.run(
        [".venv/bin/python", "scripts/print_sandbox_smoke_plan.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"enabled":false' in result.stdout.replace(" ", "")
    assert "client_secret" not in result.stdout


def test_run_cli_is_blocked_by_default_without_leaking_values():
    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/run_sandbox_dmsa_smoke.py",
            "--connection-id",
            "1",
            "--company-id",
            "company-test",
            "--project-id",
            "project-1001",
            "--confirm",
            CONFIRMATION,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "disabled" in result.stdout.casefold()
    assert "client_secret" not in result.stdout


def test_run_cli_requires_confirmation_argument():
    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/run_sandbox_dmsa_smoke.py",
            "--connection-id",
            "1",
            "--company-id",
            "company-test",
            "--project-id",
            "project-1001",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--confirm" in result.stderr


def test_public_audit_rejects_tracked_smoke_report(tmp_path):
    report = tmp_path / "accidental.smoke.json"
    report.write_text('{"status": "fake"}')
    issues = audit_paths([report])
    assert len(issues) == 1
    assert issues[0].issue_type == "tracked sandbox smoke output"
