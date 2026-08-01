from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.security_gap_closeout import ImplementationLevel, SecurityGapDomain
from app.services.security_gap_closeout import (
    ARTIFACT_FILES,
    SecurityGapCloseoutBlockedError,
    build_encryption_at_rest_guidance,
    build_known_limitations_closeout,
    build_policy_implementation_matrix,
    build_privacy_review_template,
    build_private_security_action_register,
    build_security_gap_closeout_report,
    render_policy_implementation_matrix_csv,
    validate_security_gap_closeout_report_safe,
    write_security_gap_closeout_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_and_represents_every_domain_and_level():
    report = build_security_gap_closeout_report(settings())
    assert {item.domain for item in report.domain_items} == set(SecurityGapDomain)
    assert report.domains_total == 14
    assert {item.implementation_level for item in report.policy_implementation_matrix} >= set(
        ImplementationLevel
    ) - {ImplementationLevel.OUT_OF_SCOPE}
    assert report.private_review_required
    assert report.decision == "security_gap_closeout_needs_private_review"
    assert report.encryption_at_rest_guidance_provided

    false_flags = (
        "privacy_compliance_claimed",
        "legal_compliance_claimed",
        "security_certification_claimed",
        "production_approval_granted",
        "pilot_approval_granted",
        "release_approval_granted",
        "deployment_approval_granted",
        "encryption_at_rest_implemented_by_app",
        "retention_enforcement_implemented",
        "full_audit_log_implemented",
        "notifications_implemented",
        "live_operation_attempted",
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "db_connection_attempted",
        "scanner_attempted",
        "notification_attempted",
        "deployment_attempted",
        "release_attempted",
        "package_build_attempted",
    )
    assert not any(getattr(report, name) for name in false_flags)
    validate_security_gap_closeout_report_safe(report)


def test_policy_matrix_contains_the_required_product_and_policy_rows():
    rows = " ".join(
        item.capability.casefold() for item in build_policy_implementation_matrix(settings())
    )
    for phrase in (
        "better intake ui/api",
        "better sync controls",
        "attachment processing improvements",
        "notifications",
        "audit logging",
        "data retention",
        "encryption at rest",
        "privacy compliance template",
        "threat model",
    ):
        assert phrase in rows


def test_guidance_templates_actions_and_limitations_are_safe():
    values = (
        build_privacy_review_template(settings()),
        build_encryption_at_rest_guidance(settings()),
        build_private_security_action_register(settings()),
        build_known_limitations_closeout(settings()),
    )
    assert all(values)
    for value in values:
        validate_security_gap_closeout_report_safe(value)


@pytest.mark.parametrize(
    "key",
    (
        "security_gap_closeout_require_placeholders",
        "security_gap_closeout_require_privacy_template",
        "security_gap_closeout_require_encryption_guidance",
        "security_gap_closeout_require_policy_implementation_matrix",
        "security_gap_closeout_require_private_action_register",
        "security_gap_closeout_require_no_compliance_claims",
        "security_gap_closeout_require_no_approval_claims",
    ),
)
def test_requirements_fail_closed(key):
    with pytest.raises(SecurityGapCloseoutBlockedError):
        build_security_gap_closeout_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "value",
    (
        {"raw_log": "private-value"},
        {"raw_payload": "private-value"},
        {"authorization": "Bearer private-value"},
        {"github_token": "private-value"},
        {"database_url": "postgresql://user:password-placeholder@host/db"},
        {"signed_url": "https://example.com/file?signature=private-value"},
        {"storage_key": "private/object/key"},
        {"packet_capture": "customer.pcap"},
        {"memory_dump": "process.core"},
        {"legal_notice_content": "private-value"},
        {"breach_notification_content": "private-value"},
        {"message": "production-ready"},
        {"message": "pilot approved"},
        {"message": "privacy compliant"},
        {"message": "SOC 2 certified"},
        {"message": "encryption at rest is implemented"},
        {"message": "retention enforcement is implemented"},
        {"message": "Procore endorsed"},
    ),
)
def test_validator_blocks_private_material_and_unsafe_claims(value):
    with pytest.raises(SecurityGapCloseoutBlockedError):
        validate_security_gap_closeout_report_safe(value)


def test_csv_formula_injection_and_artifact_boundaries():
    report = build_security_gap_closeout_report(settings())
    report.policy_implementation_matrix[0].public_repo_position = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA" in render_policy_implementation_matrix_csv(report)
    with TemporaryDirectory(
        prefix="procore-intake-bridge-security-gap-closeout-", dir="/tmp"
    ) as root:
        result = write_security_gap_closeout_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        for path in result.files:
            validate_security_gap_closeout_report_safe((Path(root) / path).read_text())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(SecurityGapCloseoutBlockedError):
            write_security_gap_closeout_artifacts(report, path)


def test_commands_make_docs_examples_and_quality_contract():
    commands = (
        (".venv/bin/python", "scripts/run_security_gap_closeout.py"),
        (".venv/bin/python", "scripts/print_privacy_review_template.py"),
        (".venv/bin/python", "scripts/print_encryption_at_rest_guidance.py"),
        (".venv/bin/python", "scripts/print_private_security_action_register.py"),
        (".venv/bin/python", "scripts/print_known_limitations_closeout.py"),
        (".venv/bin/python", "scripts/generate_security_gap_closeout_artifacts.py", "--temporary"),
        ("make", "security-gap-closeout"),
        ("make", "privacy-review-template"),
        ("make", "encryption-at-rest-guidance"),
        ("make", "private-security-action-register"),
        ("make", "known-limitations-closeout"),
        ("make", "security-gap-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr

    canonical = (ROOT / "docs/security-gap-closeout.md").read_text().casefold()
    for phrase in (
        "offline",
        "no live scanner",
        "no encryption implementation",
        "no retention enforcement",
        "no notifications",
        "no approval",
        "no certification",
    ):
        assert phrase in canonical
    examples = "\n".join(
        path.read_text()
        for path in (ROOT / "examples/security-gap-closeout").iterdir()
        if path.is_file()
    )
    assert "PLACEHOLDER" in examples
    makefile = (ROOT / "Makefile").read_text()
    quality = " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "security-gap-closeout",
        "privacy-review-template",
        "encryption-at-rest-guidance",
        "private-security-action-register",
        "known-limitations-closeout",
    ):
        assert target in quality
    assert "security-gap-artifact-check" not in quality


def test_audits_routes_claim_qualifiers_and_generated_output_boundaries(tmp_path):
    assert len(application_routes()) == 81 and audit_routes() == []
    unsafe = tmp_path / "security-gap-closeout.md"
    assert audit_text(unsafe, "privacy compliant")
    assert audit_text(unsafe, "encryption at rest is implemented")
    assert not audit_text(unsafe, "Encryption at rest is guidance only, not implemented.")
    assert not audit_text(unsafe, "Retention enforcement is future work.")
    generated = tmp_path / "security-gap-closeout-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])
    assert not (ROOT / ".github/workflows").is_dir() or not any(
        "security-gap" in path.name for path in (ROOT / ".github/workflows").iterdir()
    )
