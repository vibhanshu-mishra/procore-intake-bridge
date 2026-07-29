import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.usage_modes import UsageMode, UsageModeStatus
from app.services.usage_modes import (
    UsageModeBlockedError,
    build_demo_mode_readiness,
    build_pilot_mode_readiness,
    build_sandbox_mode_readiness,
    build_usage_mode_doctor_report,
    get_selected_usage_mode,
    render_usage_mode_report_markdown,
    write_usage_mode_report,
)

ROOT = Path(__file__).resolve().parents[1]


def test_default_and_valid_mode_selection() -> None:
    assert Settings().usage_mode == "demo"
    for mode in UsageMode:
        assert get_selected_usage_mode(Settings(usage_mode=mode.value)) == mode


def test_invalid_or_disallowed_mode_fails_closed() -> None:
    with pytest.raises(UsageModeBlockedError):
        get_selected_usage_mode(Settings(usage_mode="unknown"))
    with pytest.raises(UsageModeBlockedError):
        get_selected_usage_mode(
            Settings(usage_mode="pilot", allowed_usage_modes="demo,sandbox")
        )


def test_disabled_mode_is_unavailable() -> None:
    readiness = build_demo_mode_readiness(Settings(demo_mode_enabled=False))
    assert readiness.status == UsageModeStatus.UNAVAILABLE


def test_demo_is_local_fixture_only() -> None:
    readiness = build_demo_mode_readiness(Settings())
    assert readiness.status == UsageModeStatus.READY
    assert readiness.secrets_required is False
    assert readiness.external_services_required is False
    assert readiness.automatic_procore_calls is False
    assert any(
        item.requirement == "fixture_data" and item.satisfied
        for item in readiness.requirements
    )
    assert {hint.command for hint in readiness.command_hints} >= {"make demo", "make demo-sync"}


def test_sandbox_missing_private_config_is_sanitized() -> None:
    marker = "must-not-appear-client-secret"
    settings = Settings(
        usage_mode="sandbox",
        procore_environment="sandbox",
        sandbox_smoke_client_secret=marker,
    )
    readiness = build_sandbox_mode_readiness(settings)
    assert readiness.status == UsageModeStatus.NEEDS_CONFIGURATION
    assert readiness.smoke_test_manual is True
    assert readiness.automatic_procore_calls is False
    assert "allowed_scope" in {item.requirement for item in readiness.requirements}
    assert marker not in readiness.model_dump_json()


def test_pilot_requires_private_workspace_but_not_public_evidence() -> None:
    readiness = build_pilot_mode_readiness(Settings())
    assert readiness.status == UsageModeStatus.NEEDS_CONFIGURATION
    assert readiness.private_evidence_required_in_repo is False
    assert readiness.local_paths_included is False
    required = {item.requirement for item in readiness.requirements}
    assert {"customer_deployment", "support_diagnostics", "private_workspace"} <= required


def test_doctor_report_and_markdown_are_safe() -> None:
    marker = "must-not-appear-admin-token"
    report = build_usage_mode_doctor_report(Settings(admin_token=marker))
    rendered = render_usage_mode_report_markdown(report)
    serialized = report.model_dump_json()
    assert report.values_exposed is report.external_calls is report.procore_calls is False
    assert report.file_contents_included is report.local_paths_included is False
    assert marker not in serialized + rendered
    assert "sqlite:///" not in serialized + rendered
    assert str(ROOT) not in serialized + rendered
    assert report.recommended_next_steps


def test_report_writing_is_relative_and_traversal_protected(tmp_path: Path) -> None:
    report = build_usage_mode_doctor_report(Settings())
    result = write_usage_mode_report(report, tmp_path / "mode-output")
    assert result.output_directory == "demo"
    assert set(result.files) == {"mode-report.json", "mode-report.md", "manifest.json"}
    assert (tmp_path / "mode-output" / "demo" / "mode-report.json").is_file()
    with pytest.raises(UsageModeBlockedError):
        write_usage_mode_report(report, Path("../mode-output"))


@pytest.mark.parametrize(
    "script",
    [
        "print_usage_modes.py",
        "doctor.py",
        "check_local_setup.py",
        "setup_demo_mode.py",
    ],
)
def test_safe_cli_scripts(script: str) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PROCORE_INTAKE_USAGE_MODE": "demo"},
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT) not in result.stdout
    assert "must-not-appear" not in result.stdout


def test_generate_report_cli_and_traversal(tmp_path: Path) -> None:
    output = tmp_path / "mode-output"
    result = subprocess.run(
        [sys.executable, "scripts/generate_mode_report.py", "--output-root", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert str(output) not in result.stdout
    blocked = subprocess.run(
        [sys.executable, "scripts/generate_mode_report.py", "--output-root", "../mode-output"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2


def test_makefile_and_docs_describe_three_safe_modes() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "modes",
        "doctor",
        "setup-demo",
        "check-local",
        "demo",
        "demo-sync",
        "sandbox-check",
        "pilot-check",
        "mode-report",
    ):
        assert f"{target}:" in makefile
    assert "three safe paths" in (ROOT / "README.md").read_text()
    assert "no Procore credentials" in (ROOT / "docs/quickstart-demo.md").read_text()
    assert "private credentials" in (ROOT / "docs/sandbox-mode.md").read_text()
    assert "private workspace" in (ROOT / "docs/pilot-mode.md").read_text()
    assert "synthetic examples only" in (ROOT / "docs/usage-modes.md").read_text()
