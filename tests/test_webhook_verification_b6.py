import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.webhook_verification import WebhookDocsVerificationRecord
from app.services.deployment_readiness import build_deployment_readiness_report
from app.services.webhook_verification import (
    FIXTURE_NAMES,
    WebhookVerificationBlockedError,
    build_webhook_verification_plan,
    build_webhook_verification_report,
    load_synthetic_webhook_fixtures,
    run_webhook_deduplication_probe,
    run_webhook_event_queue_probe,
    run_webhook_normalizer_probe,
    run_webhook_receiver_probe,
    validate_webhook_docs_record,
    validate_webhook_fixture_payload,
    validate_webhook_verification_gates,
    write_webhook_verification_report,
)


def settings(**values):
    return Settings(_env_file=None, **values)


def verified_record(**values):
    defaults = {
        "docs_checked_at": datetime.now(UTC),
        "observed_api_version": "v2.0",
        "observed_scope_model": "company_or_project",
        "supported_event_assumptions": ["Synthetic RFI and Submittal events"],
        "signature_assumption_status": "verified",
        "payload_shape_assumption_status": "verified",
        "verified_by_operator": "example-operator",
        "status": "verified",
    }
    return WebhookDocsVerificationRecord(**(defaults | values))


def test_defaults_and_plan_are_fail_closed():
    configured = settings()
    assert configured.webhook_verification_enabled is False
    plan = build_webhook_verification_plan(configured)
    assert plan.network_calls is False
    assert plan.procore_calls is False
    assert plan.webhook_mutations is False
    with pytest.raises(WebhookVerificationBlockedError):
        validate_webhook_verification_gates(configured, "", None)


@pytest.mark.parametrize("phrase", ["", "wrong"])
def test_confirmation_is_required(phrase):
    with pytest.raises(WebhookVerificationBlockedError):
        validate_webhook_verification_gates(
            settings(webhook_verification_enabled=True), phrase, verified_record()
        )


def test_production_is_blocked_unless_allowed():
    configured = settings(webhook_verification_enabled=True, environment="production")
    with pytest.raises(WebhookVerificationBlockedError):
        validate_webhook_verification_gates(
            configured, configured.webhook_verification_confirmation_phrase, verified_record()
        )


def test_docs_required_and_verified_record_passes():
    configured = settings(webhook_verification_enabled=True)
    with pytest.raises(WebhookVerificationBlockedError):
        validate_webhook_verification_gates(
            configured, configured.webhook_verification_confirmation_phrase, None
        )
    validate_webhook_verification_gates(
        configured, configured.webhook_verification_confirmation_phrase, verified_record()
    )


def test_max_events_rejects_unsafe_value():
    with pytest.raises(ValidationError):
        settings(webhook_verification_max_events=11)


def test_docs_record_status_and_deprecated_v1():
    configured = settings()
    example = WebhookDocsVerificationRecord.model_validate_json(
        Path("examples/webhook-verification/example_docs_record.json").read_text()
    )
    assert example.status != "verified"
    assert validate_webhook_docs_record(example, configured)
    findings = validate_webhook_docs_record(
        verified_record(observed_api_version="v1.0"), configured
    )
    assert any(f.code == "deprecated_v1_only" and f.severity == "error" for f in findings)


def test_docs_record_rejects_sensitive_material():
    findings = validate_webhook_docs_record(
        verified_record(verification_notes=["Authorization: Bearer example"]), settings()
    )
    assert any(f.code in {"sensitive_content", "secret_material"} for f in findings)


def test_all_synthetic_fixtures_are_safe_and_probe_expected_behavior():
    payloads = load_synthetic_webhook_fixtures()
    assert len(payloads) == len(FIXTURE_NAMES)
    serialized = json.dumps(payloads).casefold()
    assert "authorization" not in serialized
    assert "https://" not in serialized
    assert all(validate_webhook_fixture_payload(p).status == "passed" for p in payloads)
    assert run_webhook_receiver_probe(payloads).status == "passed"
    assert run_webhook_normalizer_probe(payloads).status == "passed"
    assert run_webhook_deduplication_probe(payloads[0]).duplicate_count == 1
    assert run_webhook_event_queue_probe(payloads[0]).status == "passed"


def test_report_is_summary_only_and_output_path_is_bounded(tmp_path):
    report = build_webhook_verification_report(
        settings(webhook_verification_enabled=True), verified_record()
    )
    serialized = report.model_dump_json().casefold()
    assert "raw_payload" not in serialized
    assert "authorization" not in serialized
    assert "example-event" not in serialized
    path = write_webhook_verification_report(report, tmp_path / "reports")
    assert path.name.endswith(".webhook-verification.json")
    with pytest.raises(Exception):
        write_webhook_verification_report(report, Path("."))
    with pytest.raises(Exception):
        write_webhook_verification_report(report, Path("../outside"))


def test_cli_plan_docs_check_and_default_run_are_safe():
    plan = subprocess.run(
        [sys.executable, "scripts/print_webhook_verification_plan.py"],
        check=True, capture_output=True, text=True,
    )
    assert '"procore_calls": false' in plan.stdout
    docs = subprocess.run(
        [sys.executable, "scripts/check_webhook_docs_record.py",
         "examples/webhook-verification/example_docs_record.json"],
        check=True, capture_output=True, text=True,
    )
    assert '"status": "needs_review"' in docs.stdout
    run = subprocess.run(
        [sys.executable, "scripts/run_webhook_verification.py", "--confirm", "wrong",
         "--docs-record", "examples/webhook-verification/example_docs_record.json"],
        check=False, capture_output=True, text=True,
    )
    assert run.returncode == 2
    assert "blocked" in run.stdout.casefold()


def test_production_readiness_requires_signature_and_verified_docs():
    report = build_deployment_readiness_report(settings(environment="production"))
    assert any(f.check == "webhook_signature" and f.severity == "blocking" for f in report.findings)
    assert any(
        f.check == "webhook_verification" and f.severity == "blocking"
        for f in report.findings
    )
    local = build_deployment_readiness_report(settings(webhooks_enabled=False))
    assert not any(
        f.check == "webhook_verification" and f.severity == "blocking" for f in local.findings
    )
