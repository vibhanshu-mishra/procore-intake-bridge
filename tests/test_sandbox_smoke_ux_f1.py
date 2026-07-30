import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.sandbox_smoke_ux import SandboxSmokeUxStatus
from app.services.sandbox_smoke_ux import (
    build_sandbox_smoke_evidence_template,
    build_sandbox_smoke_ux_plan,
    render_sandbox_smoke_explanation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_smoke_ux_plan_preserves_manual_read_only_boundaries() -> None:
    plan = build_sandbox_smoke_ux_plan(Settings())
    rendered = render_sandbox_smoke_explanation(plan).casefold()
    assert plan.status == SandboxSmokeUxStatus.NEEDS_CONFIGURATION
    assert plan.command.manually_gated
    assert plan.command.read_only
    assert not plan.command.included_in_quality
    assert not plan.command.included_in_prepare_sandbox
    for phrase in (
        "read-only",
        "never automatic",
        "register or change webhooks",
        "download attachments by default",
        "write, update, approve, upload, or delete",
    ):
        assert phrase in rendered


def test_unsafe_smoke_posture_is_fail_level() -> None:
    plan = build_sandbox_smoke_ux_plan(
        Settings(
            sandbox_smoke_attachment_downloads=True,
            sandbox_smoke_require_confirmation=False,
        )
    )
    assert plan.status == SandboxSmokeUxStatus.BLOCKED
    assert any(item.fail_level for item in plan.checklist.findings)


def test_evidence_template_is_placeholder_only_and_private() -> None:
    template = build_sandbox_smoke_evidence_template()
    payload = template.model_dump_json()
    for value in template.model_dump().values():
        if isinstance(value, str):
            assert "PLACEHOLDER" in value
    assert template.private_only
    assert not template.report_contents_included
    assert "http" not in payload.casefold()
    assert str(ROOT) not in payload


@pytest.mark.parametrize(
    "script",
    (
        "check_sandbox_smoke_preflight.py",
        "explain_sandbox_smoke.py",
        "print_sandbox_smoke_evidence_template.py",
    ),
)
def test_offline_smoke_ux_clis_are_safe(script: str) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT) not in result.stdout
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout
    assert "must-not-appear" not in result.stdout


def test_preflight_treats_default_missing_config_as_planning() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_sandbox_smoke_preflight.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "needs private configuration" in result.stdout
    assert "OFFLINE ONLY" in result.stdout
    assert "makes no Procore or external calls" in result.stdout


def test_live_runner_still_refuses_without_enablement() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_sandbox_dmsa_smoke.py",
            "--connection-id",
            "1",
            "--company-id",
            "COMPANY_ID_PLACEHOLDER",
            "--project-id",
            "PROJECT_ID_PLACEHOLDER",
            "--confirm",
            "CONFIRMATION_PLACEHOLDER",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "manual enablement gate is disabled" in result.stdout
    assert "never run by quality" in result.stdout


def test_live_runner_refuses_wrong_confirmation_before_live_work() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_sandbox_dmsa_smoke.py",
            "--connection-id",
            "1",
            "--company-id",
            "COMPANY_ID_PLACEHOLDER",
            "--project-id",
            "PROJECT_ID_PLACEHOLDER",
            "--confirm",
            "WRONG_PLACEHOLDER",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PROCORE_INTAKE_SANDBOX_SMOKE_ENABLED": "true"},
    )
    assert result.returncode == 2
    assert "confirmation phrase is missing or incorrect" in result.stdout
    assert "No live call was attempted" in result.stdout


def test_make_targets_are_offline_and_live_runner_is_not_composed() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "sandbox-smoke-explain",
        "sandbox-smoke-preflight",
        "sandbox-smoke-evidence-template",
    ):
        assert f"{target}:" in makefile
        result = subprocess.run(
            ["make", target],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    prepare = makefile.split("prepare-sandbox:", 1)[1].split("\n\n", 1)[0]
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert "run_sandbox_dmsa_smoke" not in prepare
    assert "run_sandbox_dmsa_smoke" not in quality


def test_f1_docs_and_walkthrough_guidance() -> None:
    for relative in ("docs/sandbox-smoke-ux.md", "docs/sandbox-smoke-evidence.md"):
        assert (ROOT / relative).is_file()
    reference = (ROOT / "docs/command-reference.md").read_text()
    sandbox = (ROOT / "docs/walkthrough-sandbox.md").read_text()
    pilot = (ROOT / "docs/walkthrough-pilot.md").read_text()
    for command in (
        "sandbox-smoke-explain",
        "sandbox-smoke-preflight",
        "sandbox-smoke-evidence-template",
    ):
        assert command in reference
        assert command in sandbox
    assert "SANDBOX_SMOKE_REF_PLACEHOLDER" in pilot
    assert "outside Git" in (ROOT / "docs/sandbox-smoke-evidence.md").read_text()


def test_evidence_template_cli_is_valid_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/print_sandbox_smoke_evidence_template.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["smoke_ref"] == "SANDBOX_SMOKE_REF_PLACEHOLDER"
    assert payload["report_contents_included"] is False
