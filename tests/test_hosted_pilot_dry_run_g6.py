import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.hosted_pilot_dry_run import HostedPilotDryRunProfile
from app.services.hosted_pilot_dry_run import (
    ARTIFACT_FILES,
    REF_FIELDS,
    HostedPilotDryRunBlockedError,
    build_default_hosted_pilot_dry_run_profile,
    build_hosted_pilot_dry_run_report,
    sanitize_hosted_pilot_dry_run_value,
    validate_hosted_pilot_dry_run_profile,
    write_hosted_pilot_dry_run_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/hosted-pilot-dry-run"
PROFILE = EXAMPLES / "example_hosted_pilot_dry_run_profile.json"
FORBIDDEN_OUTPUT = (
    "https://",
    "postgresql://",
    "authorization: bearer",
    "-----begin",
    "/users/",
    "/private/",
    "customer.com",
    "approved for launch",
    "production-ready",
    "raw_report=",
)


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def load() -> HostedPilotDryRunProfile:
    return HostedPilotDryRunProfile.model_validate_json(
        PROFILE.read_text(encoding="utf-8")
    )


def test_default_profile_is_placeholder_only_and_offline():
    profile = build_default_hosted_pilot_dry_run_profile(settings())
    report = build_hosted_pilot_dry_run_report(profile, settings())
    assert report.status == "ready_for_private_rehearsal"
    assert report.decision == "dry_run_ready_for_private_review"
    assert report.required_refs_present == len(REF_FIELDS)
    assert not report.findings
    assert not any(
        (
            report.dry_run_execution_attempted,
            report.live_operation_attempted,
            report.deployment_attempted,
            report.procore_call_attempted,
            report.db_connection_attempted,
            report.cloud_call_attempted,
            report.webhook_registration_attempted,
            report.report_contents_exposed,
        )
    )


def test_valid_example_passes_and_maps_required_refs():
    profile = load()
    assert not validate_hosted_pilot_dry_run_profile(profile, settings())
    report = build_hosted_pilot_dry_run_report(profile, settings())
    assert report.refs_total == len(REF_FIELDS)
    assert {item.name for item in report.evidence_refs} == set(REF_FIELDS)
    assert all(item.status == "accepted_placeholder" for item in report.evidence_refs)


def test_missing_ref_needs_review():
    data = load().model_dump(mode="json")
    data["monitoring_plan_ref"] = ""
    report = build_hosted_pilot_dry_run_report(
        HostedPilotDryRunProfile.model_validate(data), settings()
    )
    assert report.status == "needs_review"
    assert report.decision == "dry_run_needs_review"
    assert report.missing_refs == ["monitoring_plan_ref"]


def test_too_many_refs_is_blocked():
    findings = validate_hosted_pilot_dry_run_profile(
        load(), settings(hosted_pilot_dry_run_max_refs=5)
    )
    assert "too_many_refs" in {item.code for item in findings}


@pytest.mark.parametrize(
    ("value", "code"),
    (
        ("https://must-not-appear.invalid/report", "raw_url"),
        ("customer.com", "real_domain"),
        (
            "postgresql://user:must-not-appear@db.invalid/app",
            "raw_url",
        ),
        ("reviewer@customer.com", "email"),
        ("312-555-0100", "phone"),
        ("123456789012345678", "long_id"),
        ("arn:aws:iam::123456789012:role/private", "cloud_id"),
        ("registry.invalid/private/app:latest", "registry_ref"),
        ("certificate=must-not-appear", "certificate_material"),
        ("csr=must-not-appear", "certificate_material"),
        ("/Users/operator/private/report", "absolute_path"),
        ("raw_report=must-not-appear", "raw_report_content"),
        ("deployment log=must-not-appear", "deployment_log"),
        ("approved for launch", "approval_claim"),
        ('{"status_code": 200, "records": ["private"]}', "live_result_payload"),
    ),
)
def test_unsafe_values_are_blocked(value, code):
    data = load().model_dump(mode="json")
    data["notes"] = [value]
    findings = validate_hosted_pilot_dry_run_profile(
        HostedPilotDryRunProfile.model_validate(data), settings()
    )
    assert code in {item.code for item in findings}


def test_unsafe_allowance_settings_fail_closed():
    findings = validate_hosted_pilot_dry_run_profile(
        load(), settings(hosted_pilot_dry_run_allow_real_urls=True)
    )
    assert "unsafe_policy" in {item.code for item in findings}


def test_sanitizer_suppresses_private_values():
    unsafe = {
        "url": "https://must-not-appear.invalid",
        "secret": "Authorization: Bearer must-not-appear",
        "path": Path("/Users/operator/private"),
    }
    serialized = json.dumps(
        sanitize_hosted_pilot_dry_run_value(unsafe)
    ).casefold()
    assert "must-not-appear" not in serialized
    assert "/users/" not in serialized


def test_generated_artifacts_are_contained_and_safe(tmp_path: Path):
    output = tmp_path / "procore-intake-bridge-hosted-pilot-dry-run-pytest"
    result = write_hosted_pilot_dry_run_artifacts(load(), output)
    assert result.files == ARTIFACT_FILES
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file()
    ).casefold()
    assert "placeholder" in contents
    assert not any(value in contents for value in FORBIDDEN_OUTPUT)
    assert result.live_operations is False
    assert result.deployment_attempted is False
    assert result.private_values_exposed is False


def test_artifact_generation_blocks_traversal():
    with pytest.raises(HostedPilotDryRunBlockedError):
        write_hosted_pilot_dry_run_artifacts(
            load(), Path("../hosted-pilot-dry-run-output")
        )


@pytest.mark.parametrize(
    "command",
    (
        ["print_hosted_pilot_dry_run_template.py"],
        [
            "check_hosted_pilot_dry_run.py",
            "examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json",
        ],
        ["print_hosted_pilot_dry_run_matrix.py"],
        [
            "generate_hosted_pilot_dry_run_artifacts.py",
            "examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json",
            "--temporary",
        ],
    ),
)
def test_g6_cli_commands_are_offline_and_safe(command):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / command[0]), *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = (result.stdout + result.stderr).casefold()
    assert not any(value in output for value in FORBIDDEN_OUTPUT)


def test_examples_are_placeholder_only():
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in EXAMPLES.iterdir()
        if path.is_file()
    ).casefold()
    assert "placeholder" in contents
    assert not any(value in contents for value in FORBIDDEN_OUTPUT)


def test_makefile_and_docs_contract():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = (
        "hosted-pilot-dry-run-template",
        "hosted-pilot-dry-run-check",
        "hosted-pilot-dry-run-matrix",
        "hosted-pilot-dry-run-artifact-check",
    )
    for target in targets:
        assert f"{target}:" in makefile
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in targets[:3]:
        assert target in quality
    assert targets[3] not in quality
    docs = (
        "hosted-pilot-dry-run.md",
        "pilot-operations-rehearsal.md",
        "hosted-pilot-evidence-map.md",
    )
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    for name in docs:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").casefold()
        assert name in nav
        assert "not" in text and ("launch" in text or "pilot approval" in text)
        assert "live operation" in text
