import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.https_webhook_planning import HttpsWebhookPlanningProfile
from app.services.https_webhook_planning import (
    ARTIFACT_FILES,
    HttpsWebhookPlanningBlockedError,
    build_default_https_webhook_profile,
    build_https_webhook_report,
    sanitize_https_webhook_value,
    validate_https_webhook_profile,
    write_https_webhook_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/https-webhook-planning"
PROFILE = EXAMPLES / "example_https_webhook_profile.json"
FORBIDDEN_OUTPUT = (
    "https://",
    "postgresql://",
    "authorization: bearer",
    "-----begin",
    "_acme-challenge.",
    "/users/",
    "/private/",
    "customer.com",
)


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def load() -> HttpsWebhookPlanningProfile:
    return HttpsWebhookPlanningProfile.model_validate_json(
        PROFILE.read_text(encoding="utf-8")
    )


def test_default_profile_is_placeholder_only_and_offline():
    profile = build_default_https_webhook_profile(settings())
    report = build_https_webhook_report(profile, settings())
    assert report.status == "needs_configuration"
    assert report.endpoint_path_expected == "/webhooks/procore"
    assert report.webhook_registration_attempted is False
    assert report.dns_check_attempted is False
    assert report.tls_check_attempted is False
    assert report.public_url_check_attempted is False
    assert report.procore_call_attempted is False
    assert not report.findings


def test_valid_example_passes():
    profile = load()
    assert not validate_https_webhook_profile(profile, settings())
    report = build_https_webhook_report(profile, settings())
    assert report.tls_plan_present
    assert report.dns_plan_present
    assert report.signature_secret_ref_present
    assert report.event_queue_present
    assert report.replay_plan_present
    assert report.disable_plan_present
    assert report.rollback_plan_present


@pytest.mark.parametrize(
    ("value", "code"),
    (
        ("https://must-not-appear.invalid/webhooks/procore", "raw_url"),
        ("customer.com", "real_domain"),
        ("A customer.invalid 192.0.2.1", "dns_record"),
        ("-----BEGIN CERTIFICATE-----", "certificate"),
        ("-----BEGIN PRIVATE KEY-----", "certificate"),
        ("-----BEGIN CERTIFICATE REQUEST-----", "csr"),
        ("acme_challenge=must-not-appear", "acme_value"),
        ("webhook_secret=must-not-appear", "secret"),
        ("Authorization: Bearer must-not-appear", "secret"),
        (
            "postgresql://must-not-appear:must-not-appear@must-not-appear.invalid/db",
            "raw_url",
        ),
        ("vpc-abcdef123456", "infrastructure_id"),
        ("/Users/operator/private-webhook", "absolute_path"),
        ("webhook_id=12345678", "webhook_id"),
        ("raw_payload=must-not-appear", "webhook_report_contents"),
        ("production setup is complete", "approval_claim"),
    ),
)
def test_unsafe_values_are_blocked(value, code):
    data = load().model_dump(mode="json")
    data["notes"] = [value]
    findings = validate_https_webhook_profile(
        HttpsWebhookPlanningProfile.model_validate(data), settings()
    )
    assert code in {item.code for item in findings}


def test_path_must_match_local_application_expectation():
    data = load().model_dump(mode="json")
    data["expected_webhook_path"] = "/different/path"
    findings = validate_https_webhook_profile(
        HttpsWebhookPlanningProfile.model_validate(data), settings()
    )
    assert {"unexpected_webhook_path", "unsupported_webhook_path"} <= {
        item.code for item in findings
    }


def test_unsafe_allowance_settings_fail_closed():
    findings = validate_https_webhook_profile(
        load(), settings(https_webhook_allow_real_urls=True)
    )
    assert "unsafe_policy" in {item.code for item in findings}


def test_sanitizer_suppresses_private_values():
    unsafe = {
        "url": "https://must-not-appear.invalid",
        "secret": "webhook_secret=must-not-appear",
        "path": Path("/Users/operator/private-webhook"),
    }
    serialized = json.dumps(sanitize_https_webhook_value(unsafe)).casefold()
    assert "must-not-appear" not in serialized
    assert "/users/" not in serialized


def test_generated_artifacts_are_contained_and_safe(tmp_path: Path):
    output = tmp_path.parent / "procore-intake-bridge-https-webhook-pytest"
    result = write_https_webhook_artifacts(load(), output)
    assert result.files == ARTIFACT_FILES
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file()
    ).casefold()
    assert "placeholder" in contents
    assert "/webhooks/procore" in contents
    assert not any(value in contents for value in FORBIDDEN_OUTPUT)
    assert result.external_calls is False
    assert result.webhook_registration_attempted is False
    assert result.certificate_generated is False


def test_artifact_generation_blocks_traversal():
    with pytest.raises(HttpsWebhookPlanningBlockedError):
        write_https_webhook_artifacts(load(), Path("../https-webhook-output"))


@pytest.mark.parametrize(
    "command",
    (
        ["print_https_webhook_template.py"],
        [
            "check_https_webhook_plan.py",
            "examples/https-webhook-planning/example_https_webhook_profile.json",
        ],
        ["print_webhook_ingress_matrix.py"],
        ["print_webhook_disable_plan.py"],
        [
            "generate_https_webhook_artifacts.py",
            "examples/https-webhook-planning/example_https_webhook_profile.json",
            "--temporary",
        ],
    ),
)
def test_g5_cli_commands_are_offline_and_safe(command):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / command[0]), *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
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
    for target in (
        "https-webhook-template",
        "https-webhook-check",
        "https-webhook-matrix",
        "webhook-disable-plan",
        "https-webhook-artifact-check",
    ):
        assert f"{target}:" in makefile
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "https-webhook-template",
        "https-webhook-check",
        "https-webhook-matrix",
        "webhook-disable-plan",
    ):
        assert target in quality
    assert "https-webhook-artifact-check" not in quality
    for name in (
        "https-webhook-production-planning.md",
        "webhook-ingress-planning.md",
        "tls-dns-planning.md",
        "webhook-disable-rollback.md",
    ):
        assert (ROOT / "docs" / name).is_file()
        assert name in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
