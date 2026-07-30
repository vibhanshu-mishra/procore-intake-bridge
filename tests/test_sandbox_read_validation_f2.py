import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.sandbox_read_validation import (
    SandboxReadValidationDecision,
    SandboxReadValidationStatus,
)
from app.services.sandbox_read_validation import (
    ARTIFACT_NAMES,
    CONFIRMATION_PHRASE,
    SandboxReadValidationBlockedError,
    build_sandbox_read_preflight,
    build_sandbox_read_validation_plan,
    classify_procore_read_error,
    hash_sandbox_identifier,
    mask_sandbox_identifier,
    run_sandbox_read_validation,
    sanitize_sandbox_read_value,
    validate_sandbox_read_report_safe,
    write_sandbox_read_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]


def live_settings(**updates) -> Settings:
    values = {
        "sandbox_read_validation_enabled": True,
        "sandbox_read_validation_confirmation": CONFIRMATION_PHRASE,
        "procore_live_mode_enabled": True,
        "procore_environment": "sandbox",
        "sandbox_smoke_connection_id": 1,
        "sandbox_smoke_company_id": "COMPANY_SCOPE_TEST_VALUE",
        "sandbox_smoke_project_id": "PROJECT_SCOPE_TEST_VALUE",
    }
    values.update(updates)
    return Settings(_env_file=None, **values)


class FakeReadClient:
    credential_refs_configured = True
    sandbox_environment = True
    allowed_scope_configured = True

    def __init__(self, rfis=None, submittals=None):
        self.rfis = rfis if rfis is not None else []
        self.submittals = submittals if submittals is not None else []
        self.calls: list[str] = []

    def list_rfis(self, *, page, per_page, updated_since):
        self.calls.append(f"rfis-list-{page}")
        return self.rfis if page == 1 else []

    def get_rfi(self, identifier):
        self.calls.append("rfi-detail")
        return {"id": identifier, "subject": "MUST_NOT_APPEAR_RFI_SUBJECT"}

    def list_submittals(self, *, page, per_page, updated_since):
        self.calls.append(f"submittals-list-{page}")
        return self.submittals if page == 1 else []

    def get_submittal(self, identifier):
        self.calls.append("submittal-detail")
        return {"id": identifier, "title": "MUST_NOT_APPEAR_SUBMITTAL_TITLE"}


def test_preflight_and_plan_are_offline() -> None:
    report = build_sandbox_read_preflight(Settings(_env_file=None))
    plan = build_sandbox_read_validation_plan(Settings(_env_file=None))
    for value in (report, plan):
        assert not value.validation_attempted
        assert not value.live_calls_attempted
        assert value.decision == SandboxReadValidationDecision.VALIDATION_NOT_RUN
        assert not value.output_policy.external_calls_from_planning
        assert value.max_projects <= 3
        assert value.max_items_per_tool <= 5
        assert value.max_pages <= 2


@pytest.mark.parametrize(
    ("update", "value"),
    (
        ("sandbox_read_validation_enabled", False),
        ("sandbox_read_validation_confirmation", ""),
        ("procore_environment", "production"),
        ("sandbox_smoke_company_id", None),
        ("sandbox_smoke_project_id", None),
        ("sandbox_smoke_connection_id", None),
    ),
)
def test_live_validation_blocks_missing_gates(update: str, value) -> None:
    with pytest.raises(SandboxReadValidationBlockedError):
        run_sandbox_read_validation(
            live_settings(**{update: value}),
            FakeReadClient(),
        )


def test_live_validation_blocks_missing_dmsa_refs() -> None:
    client = FakeReadClient()
    client.credential_refs_configured = False
    with pytest.raises(SandboxReadValidationBlockedError):
        run_sandbox_read_validation(live_settings(), client)


def test_injected_client_summarizes_lists_and_details_without_content() -> None:
    rfi_id = "RFI_RAW_TEST_IDENTIFIER_8675309"
    submittal_id = "SUBMITTAL_RAW_TEST_IDENTIFIER_246810"
    client = FakeReadClient(
        rfis=[{"id": rfi_id, "subject": "MUST_NOT_APPEAR_RFI_SUBJECT"}],
        submittals=[
            {"id": submittal_id, "title": "MUST_NOT_APPEAR_SUBMITTAL_TITLE"}
        ],
    )
    report = run_sandbox_read_validation(live_settings(), client)
    assert report.decision == SandboxReadValidationDecision.VALIDATION_PASSED
    assert report.validation_attempted and report.live_calls_attempted
    assert set(client.calls) >= {
        "rfis-list-1",
        "rfi-detail",
        "submittals-list-1",
        "submittal-detail",
    }
    serialized = report.model_dump_json()
    for private_value in (
        rfi_id,
        submittal_id,
        "MUST_NOT_APPEAR_RFI_SUBJECT",
        "MUST_NOT_APPEAR_SUBMITTAL_TITLE",
        str(ROOT),
    ):
        assert private_value not in serialized
    assert hash_sandbox_identifier(rfi_id) in serialized
    assert hash_sandbox_identifier(submittal_id) in serialized
    validate_sandbox_read_report_safe(report)


def test_empty_results_are_valid_and_informative() -> None:
    report = run_sandbox_read_validation(live_settings(), FakeReadClient())
    assert report.decision == SandboxReadValidationDecision.VALIDATION_PASSED
    assert all(
        result.status == SandboxReadValidationStatus.EMPTY_RESULT
        for result in report.tool_summaries
    )


class PaginatedClient(FakeReadClient):
    def list_rfis(self, *, page, per_page, updated_since):
        self.calls.append(f"rfis-list-{page}")
        return [{"id": f"RFI_TEST_PAGE_{page}_{index}"} for index in range(per_page)]

    def list_submittals(self, *, page, per_page, updated_since):
        self.calls.append(f"submittals-list-{page}")
        return [
            {"id": f"SUBMITTAL_TEST_PAGE_{page}_{index}"}
            for index in range(per_page)
        ]


def test_pagination_is_bounded_by_pages_and_item_cap() -> None:
    client = PaginatedClient()
    report = run_sandbox_read_validation(live_settings(), client)
    assert all(result.pages_attempted == 2 for result in report.tool_summaries)
    assert all(result.sanitized_item_count == 5 for result in report.tool_summaries)
    assert not any(call.endswith("-3") for call in client.calls)


class ReadError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class PermissionClient(FakeReadClient):
    def list_rfis(self, *, page, per_page, updated_since):
        raise ReadError(403, "private raw API error with https://must-not-appear.invalid")


def test_permission_not_found_and_generic_errors_are_categorized() -> None:
    assert classify_procore_read_error(ReadError(403, "hidden")) == (
        SandboxReadValidationStatus.PERMISSION_DENIED
    )
    assert classify_procore_read_error(ReadError(404, "hidden")) == (
        SandboxReadValidationStatus.NOT_FOUND
    )
    assert classify_procore_read_error(RuntimeError("hidden")) == (
        SandboxReadValidationStatus.ERROR
    )
    report = run_sandbox_read_validation(live_settings(), PermissionClient())
    assert report.decision == SandboxReadValidationDecision.VALIDATION_NEEDS_REVIEW
    assert report.tool_summaries[0].status == SandboxReadValidationStatus.PERMISSION_DENIED
    assert "must-not-appear" not in report.model_dump_json()


def test_sanitization_and_identifier_helpers() -> None:
    raw = {
        "id": "RAW_ID_MUST_NOT_APPEAR",
        "subject": "PRIVATE_SUBJECT",
        "client_secret": "TEST_SECRET_PLACEHOLDER",
        "url": "https://private.invalid/item",
    }
    sanitized = json.dumps(sanitize_sandbox_read_value(raw))
    for value in raw.values():
        assert value not in sanitized
    assert mask_sandbox_identifier("123456") == "masked:6"
    assert hash_sandbox_identifier("123456") != "123456"


def test_output_policy_and_artifacts_remain_safe(tmp_path: Path) -> None:
    report = run_sandbox_read_validation(live_settings(), FakeReadClient())
    assert not report.output_policy.attachments_included
    assert not report.output_policy.attachment_downloads_attempted
    assert not report.output_policy.raw_payloads_stored
    assert not report.output_policy.secrets_exposed
    assert not report.output_policy.ids_exposed
    root = tmp_path / "sandbox-read-output"
    result = write_sandbox_read_artifacts(report, root)
    assert result.files == ARTIFACT_NAMES
    assert set(path.name for path in root.iterdir()) == set(ARTIFACT_NAMES)
    for path in root.iterdir():
        assert str(tmp_path) not in path.read_text()


@pytest.mark.parametrize(
    "script",
    (
        "print_sandbox_read_plan.py",
        "check_sandbox_read_preflight.py",
        "print_sandbox_read_evidence_template.py",
    ),
)
def test_offline_clis_run_safely(script: str) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT) not in result.stdout
    assert "http://" not in result.stdout and "https://" not in result.stdout


def test_live_cli_refuses_before_any_live_work() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_sandbox_read_validation.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "manual enablement is disabled" in result.stdout
    assert "No live call was attempted" in result.stdout
    assert str(ROOT) not in result.stdout


def test_make_targets_separate_offline_and_live_paths() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "sandbox-read-plan",
        "sandbox-read-preflight",
        "sandbox-read-evidence-template",
        "sandbox-read-validation",
    ):
        assert f"{target}:" in makefile
    for target in (
        "sandbox-read-plan",
        "sandbox-read-preflight",
        "sandbox-read-evidence-template",
    ):
        result = subprocess.run(
            ["make", target],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    live = subprocess.run(
        ["make", "sandbox-read-validation"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert live.returncode != 0
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    prepare = makefile.split("prepare-sandbox:", 1)[1].splitlines()[0]
    assert "sandbox-read-validation" not in quality
    assert "sandbox-read-validation" not in prepare
    assert all(
        target in quality
        for target in (
            "sandbox-read-plan",
            "sandbox-read-preflight",
            "sandbox-read-evidence-template",
        )
    )


def test_docs_and_examples_are_placeholder_only() -> None:
    validation = (ROOT / "docs/sandbox-read-validation.md").read_text().casefold()
    evidence = (ROOT / "docs/sandbox-read-evidence.md").read_text().casefold()
    assert "never automatic" in validation
    for phrase in (
        "does not write to procore",
        "register webhooks",
        "download attachments by default",
        "store raw payloads",
    ):
        assert phrase in validation
    assert "outside git" in evidence
    sandbox = (ROOT / "docs/walkthrough-sandbox.md").read_text().casefold()
    assert all(
        command in sandbox
        for command in (
            "make sandbox-read-plan",
            "make sandbox-read-preflight",
            "make sandbox-read-evidence-template",
        )
    )
    assert "do not run it as part of this walkthrough" in sandbox
    assert "sandbox_read_validation_ref_placeholder" in (
        ROOT / "docs/walkthrough-pilot.md"
    ).read_text().casefold()

    example_root = ROOT / "examples/sandbox-read-validation"
    combined = "\n".join(path.read_text() for path in example_root.iterdir())
    for placeholder in (
        "SANDBOX_READ_VALIDATION_REF_PLACEHOLDER",
        "SANDBOX_READ_RUN_LABEL_PLACEHOLDER",
        "SANDBOX_SCOPE_REF_PLACEHOLDER",
        "SANDBOX_RFI_ACCESS_STATUS_PLACEHOLDER",
        "SANDBOX_SUBMITTAL_ACCESS_STATUS_PLACEHOLDER",
        "SANDBOX_PAGINATION_STATUS_PLACEHOLDER",
        "SANDBOX_DATE_FILTER_STATUS_PLACEHOLDER",
        "SANDBOX_REVIEWER_PLACEHOLDER",
        "SANDBOX_EXPIRY_PLACEHOLDER",
    ):
        assert placeholder in combined
    assert "http://" not in combined and "https://" not in combined
