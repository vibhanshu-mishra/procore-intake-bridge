import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.sandbox_pilot_flow import FlowDecision, FlowProfile, FlowStage
from app.services.sandbox_pilot_flow import (
    SandboxPilotFlowBlockedError,
    build_default_flow_template,
    build_sandbox_pilot_flow_report,
    validate_flow_profile,
    write_sandbox_pilot_flow_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/sandbox-pilot-flow"


def settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load(name: str) -> FlowProfile:
    return FlowProfile.model_validate_json((EXAMPLES / name).read_text())


@pytest.mark.parametrize(
    "name", ["example_demo_flow.json", "example_sandbox_flow.json", "example_pilot_flow.json"]
)
def test_examples_validate(name: str) -> None:
    assert validate_flow_profile(load(name), settings()) == []


def test_invalid_path_is_rejected() -> None:
    with pytest.raises((ValidationError, SandboxPilotFlowBlockedError)):
        build_default_flow_template("invalid", settings())


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("customer-build.com", "domain"),
        ("https://service.invalid/path", "raw_url"),
        ("postgresql://user:placeholder@database.invalid/name", "raw_url"),
        ("client_secret=private-value", "secret"),
        ("Authorization: Bearer must-not-appear", "secret"),
        ("https://files.invalid/x?signature=value", "raw_url"),
        ("-----BEGIN PRIVATE KEY-----", "certificate"),
        ("vpc-abc12345", "infrastructure_id"),
        ("/Users/operator/private.json", "absolute_path"),
        ("PRIVATE_VALUE=real-value", "env_assignment"),
        ("backup.dump", "blocked_file"),
        ("raw smoke report contents", "raw_content"),
        ("operator@customer.invalid", "email"),
        ("312-555-0199", "phone"),
        ("Procore company 87654321", "procore_id"),
        ("reviewer Jane Smith", "identity"),
    ],
)
def test_unsafe_values_blocked(value: str, code: str) -> None:
    profile = load("example_pilot_flow.json")
    profile.notes = [value]
    assert code in {item.code for item in validate_flow_profile(profile, settings())}


def test_production_and_disabled_flow_are_blocked() -> None:
    profile = load("example_pilot_flow.json")
    profile.environment_label = "production"
    assert "production" in {item.code for item in validate_flow_profile(profile, settings())}
    profile.environment_label = "EXAMPLE_PILOT_PLACEHOLDER"
    report = build_sandbox_pilot_flow_report(profile, settings(sandbox_pilot_flow_enabled=False))
    assert report.decision == FlowDecision.BLOCKED


def test_path_decisions_never_approve() -> None:
    demo = build_sandbox_pilot_flow_report(load("example_demo_flow.json"), settings())
    assert demo.decision == FlowDecision.DEMO_READY
    sandbox = build_sandbox_pilot_flow_report(load("example_sandbox_flow.json"), settings())
    assert sandbox.decision == FlowDecision.SANDBOX_NEEDS_CONFIGURATION
    assert {
        "dmsa_secret_refs",
        "allowed_project_scope",
        "admin_auth",
        "sandbox_smoke_evidence",
    } <= {r.requirement for r in sandbox.requirements}
    pilot = build_sandbox_pilot_flow_report(load("example_pilot_flow.json"), settings())
    assert pilot.decision == FlowDecision.PILOT_NEEDS_CONFIGURATION
    assert {
        "private_workspace",
        "evidence_review",
        "approval_packet_private_review",
        "deployment_recipe",
        "postgres_database",
        "storage_provider",
        "rollback_plan",
        "backup_plan",
    } <= {r.requirement for r in pilot.requirements}
    assert all(not report.pilot_approved for report in (demo, sandbox, pilot))
    assert {item.stage for item in pilot.milestones} == set(FlowStage)


def test_artifacts_are_contained_and_safe(tmp_path: Path) -> None:
    root = tmp_path / "sandbox-pilot-output"
    result = write_sandbox_pilot_flow_artifacts(load("example_pilot_flow.json"), root)
    assert result.output_directory.endswith("/example-pilot-flow")
    files = list(root.rglob("*"))
    assert all(path.resolve().is_relative_to(root.resolve()) for path in files)
    text = "\n".join(path.read_text() for path in files if path.is_file())
    for forbidden in ("Authorization:", "postgresql://", "/Users/", "customer-build.com"):
        assert forbidden not in text
    with pytest.raises(SandboxPilotFlowBlockedError):
        write_sandbox_pilot_flow_artifacts(load("example_pilot_flow.json"), Path("../escape"))


def test_cli_contracts(tmp_path: Path) -> None:
    commands = [
        [sys.executable, "scripts/print_sandbox_to_pilot_plan.py"],
        [sys.executable, "scripts/print_sandbox_pilot_flow_template.py", "--path", "demo"],
        [sys.executable, "scripts/print_sandbox_pilot_flow_template.py", "--path", "sandbox"],
        [sys.executable, "scripts/print_sandbox_pilot_flow_template.py", "--path", "pilot"],
        [
            sys.executable,
            "scripts/check_sandbox_onboarding.py",
            str(EXAMPLES / "example_sandbox_flow.json"),
        ],
        [
            sys.executable,
            "scripts/check_pilot_preflight.py",
            str(EXAMPLES / "example_pilot_flow.json"),
        ],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        assert completed.returncode == 0, completed.stderr
        assert str(ROOT) not in completed.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_sandbox_pilot_flow_artifacts.py",
            str(EXAMPLES / "example_pilot_flow.json"),
            "--output-root",
            str(tmp_path / "output"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert generated.returncode == 0
    assert str(tmp_path) not in generated.stdout
    assert json.loads(generated.stdout)["external_calls"] is False
