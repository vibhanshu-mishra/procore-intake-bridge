from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.final_security_review import FinalSecurityDomain
from app.services.final_security_review import (
    ARTIFACT_FILES,
    FinalSecurityReviewBlockedError,
    build_final_security_dependencies,
    build_final_security_review_report,
    render_final_security_review_markdown,
    render_security_domain_matrix_csv,
    validate_final_security_review_report_safe,
    write_final_security_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_report_builds_offline_with_dependencies_domains_gates_and_gaps():
    report = build_final_security_review_report(settings())
    assert set(summary.domain for summary in report.domain_summaries) == set(FinalSecurityDomain)
    assert report.domains_total == 14
    assert report.gates_total == len(report.gates)
    assert report.gaps_total == len(report.gaps)
    assert report.gates and report.gaps
    dependency_names = " ".join(
        item.name.casefold() for item in build_final_security_dependencies(settings())
    )
    for marker in (
        "i1",
        "i2",
        "i3",
        "i4",
        "i5",
        "i6",
        "i7",
        "public safety",
        "route audit",
        "docs-site",
    ):
        assert marker in dependency_names
    assert report.private_review_required
    assert report.decision == "final_security_needs_private_review"
    assert not any(
        (
            report.production_approval_granted,
            report.pilot_approval_granted,
            report.release_approval_granted,
            report.security_certification_claimed,
            report.legal_compliance_claimed,
            report.live_operation_attempted,
            report.external_call_attempted,
            report.procore_call_attempted,
            report.cloud_call_attempted,
            report.db_connection_attempted,
            report.scanner_attempted,
            report.notification_attempted,
            report.deployment_attempted,
            report.release_attempted,
            report.package_build_attempted,
        )
    )
    validate_final_security_review_report_safe(report)


@pytest.mark.parametrize(
    "key",
    (
        "final_security_review_require_placeholders",
        "final_security_review_require_i1_threat_model",
        "final_security_review_require_i2_auth_boundary",
        "final_security_review_require_i3_webhook_security",
        "final_security_review_require_i4_data_policy",
        "final_security_review_require_i5_infra_security",
        "final_security_review_require_i6_supply_chain",
        "final_security_review_require_i7_incident_response",
        "final_security_review_require_public_safety_audit",
        "final_security_review_require_route_audit",
        "final_security_review_require_private_review_gaps",
    ),
)
def test_requirements_fail_closed(key):
    with pytest.raises(FinalSecurityReviewBlockedError):
        build_final_security_review_report(settings(**{key: False}))


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
        {"message": "SOC 2 certified"},
        {"message": "Procore endorsed"},
        {"message": "reviewer@example.com"},
    ),
)
def test_validator_blocks_private_material_and_claims(value):
    with pytest.raises(FinalSecurityReviewBlockedError):
        validate_final_security_review_report_safe(value)


def test_renderers_csv_and_artifacts_are_safe():
    report = build_final_security_review_report(settings())
    report.domain_summaries[0].summary = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA" in render_security_domain_matrix_csv(report)
    validate_final_security_review_report_safe(render_final_security_review_markdown(report))
    with TemporaryDirectory(prefix="procore-intake-bridge-final-security-", dir="/tmp") as root:
        result = write_final_security_review_artifacts(report, Path(root))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
        for path in result.files:
            validate_final_security_review_report_safe((Path(root) / path).read_text())
    for path in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(FinalSecurityReviewBlockedError):
            write_final_security_review_artifacts(report, path)


def test_commands_make_docs_examples_and_quality_contract():
    commands = (
        (".venv/bin/python", "scripts/run_final_security_review.py"),
        (".venv/bin/python", "scripts/print_security_readiness_summary.py"),
        (".venv/bin/python", "scripts/print_security_gap_register.py"),
        (".venv/bin/python", "scripts/print_private_security_review_checklist.py"),
        (".venv/bin/python", "scripts/generate_final_security_review_artifacts.py", "--temporary"),
        ("make", "final-security-review"),
        ("make", "security-readiness-summary"),
        ("make", "security-gap-register"),
        ("make", "private-security-review-checklist"),
        ("make", "final-security-artifact-check"),
    )
    for command in commands:
        result = run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr

    canonical = (ROOT / "docs/final-security-readiness-review.md").read_text().casefold()
    assert all(
        phrase in canonical
        for phrase in (
            "offline",
            "i1",
            "i7",
            "grants no",
            "approval",
            "claims no",
            "certification",
            "private security review",
        )
    )
    example_text = "\n".join(
        path.read_text()
        for path in (ROOT / "examples/final-security-review").iterdir()
        if path.is_file()
    )
    assert "PLACEHOLDER" in example_text
    makefile = (ROOT / "Makefile").read_text()
    assert (
        "quality: final-security-review security-readiness-summary security-gap-register "
        "private-security-review-checklist" in makefile
    )
    quality_header = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "final-security-artifact-check" not in quality_header


def test_audits_routes_and_generated_output_boundaries(tmp_path):
    assert len(application_routes()) == 81 and audit_routes() == []
    unsafe = tmp_path / "final-security-review.md"
    assert audit_text(unsafe, "github_token=private-value")
    assert audit_text(unsafe, "production approved")
    generated = tmp_path / "final-security-review-output" / "report.md"
    generated.parent.mkdir()
    generated.write_text("placeholder")
    assert audit_paths([generated])
    assert not (ROOT / ".github/workflows").is_dir() or not any(
        "final-security" in path.name for path in (ROOT / ".github/workflows").iterdir()
    )
