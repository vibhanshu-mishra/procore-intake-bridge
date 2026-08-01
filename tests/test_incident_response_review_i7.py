from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.incident_response_review import (
    AuditLogBoundary,
    ForensicsEvidenceType,
    IncidentCategory,
    IncidentSeverity,
)
from app.services.incident_response_review import (
    ARTIFACT_FILES,
    IncidentResponseReviewBlockedError,
    _cell,
    build_incident_response_review_report,
    render_incident_response_review_markdown,
    validate_incident_response_review_report_safe,
    write_incident_response_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def settings(**kw):
    return Settings(_env_file=None, **kw)


def test_report_complete_offline():
    r = build_incident_response_review_report(settings())
    assert r.status == "needs_review"
    assert set(r.categories) == set(IncidentCategory)
    assert set(r.severities) == set(IncidentSeverity)
    assert set(r.audit_log_boundaries) == set(AuditLogBoundary)
    assert set(r.forensics_evidence_types) == set(ForensicsEvidenceType)
    assert (
        r.categories_total,
        r.severities_total,
        r.audit_log_boundaries_total,
        r.forensics_evidence_types_total,
        r.scenario_matrix_items_total,
    ) == (19, 6, 18, 15, 19)
    assert not any(
        (
            r.live_incident_response_attempted,
            r.external_call_attempted,
            r.procore_call_attempted,
            r.cloud_call_attempted,
            r.db_connection_attempted,
            r.scanner_attempted,
            r.notification_attempted,
            r.forensics_tool_attempted,
            r.log_collection_attempted,
            r.packet_capture_attempted,
            r.evidence_collection_attempted,
            r.deletion_or_purge_attempted,
            r.secrets_exposed,
            r.raw_logs_exposed,
            r.raw_payloads_exposed,
        )
    )
    validate_incident_response_review_report_safe(r)


@pytest.mark.parametrize(
    "key",
    (
        "incident_response_review_require_placeholders",
        "incident_response_review_require_private_evidence_references",
        "incident_response_review_require_no_raw_logs",
        "incident_response_review_require_no_secret_values",
        "incident_response_review_require_no_payload_dumps",
        "incident_response_review_require_audit_log_boundary_map",
        "incident_response_review_require_chain_of_custody_placeholders",
        "incident_response_review_require_runbooks",
        "incident_response_review_require_generated_output_ignores",
    ),
)
def test_requirements_fail_closed(key):
    with pytest.raises(IncidentResponseReviewBlockedError):
        build_incident_response_review_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "value",
    (
        {"raw_log": "private-value"},
        {"raw_payload": "private-value"},
        {"packet_capture": "private-value"},
        {"memory_dump": "private-value"},
        {"forensic_image": "private-value"},
        {"legal_notice": "private-value"},
        {"breach_notification_content": "private-value"},
        {"message": "breach readiness certified"},
        {"message": "production-ready"},
        {"message": "reviewer@example.com"},
    ),
)
def test_validator_blocks(value):
    with pytest.raises(IncidentResponseReviewBlockedError):
        validate_incident_response_review_report_safe(value)


def test_render_csv_artifacts_roots():
    r = build_incident_response_review_report(settings())
    assert _cell("=FORMULA_PLACEHOLDER") == "'=FORMULA_PLACEHOLDER"
    validate_incident_response_review_report_safe(render_incident_response_review_markdown(r))
    with TemporaryDirectory(prefix="procore-intake-bridge-incident-response-", dir="/tmp") as d:
        x = write_incident_response_review_artifacts(r, Path(d))
        assert set(x.files) == set(ARTIFACT_FILES) and not x.live_operations
    for p in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(IncidentResponseReviewBlockedError):
            write_incident_response_review_artifacts(r, p)


def test_commands_make_audits(tmp_path):
    commands = (
        (".venv/bin/python", "scripts/run_incident_response_review.py"),
        (".venv/bin/python", "scripts/print_incident_runbook.py"),
        (".venv/bin/python", "scripts/print_audit_log_boundary_map.py"),
        (".venv/bin/python", "scripts/print_forensics_evidence_checklist.py"),
        (
            ".venv/bin/python",
            "scripts/generate_incident_response_review_artifacts.py",
            "--temporary",
        ),
        ("make", "incident-response-review"),
        ("make", "incident-runbook"),
        ("make", "audit-log-boundary-map"),
        ("make", "forensics-evidence-checklist"),
        ("make", "incident-response-artifact-check"),
    )
    for c in commands:
        x = run(c, cwd=ROOT, text=True, capture_output=True)
        assert x.returncode == 0, x.stdout + x.stderr
    p = tmp_path / "incident-response-review.md"
    assert audit_text(p, "raw_log=private-value")
    g = tmp_path / "incident-response-review-output" / "r.md"
    g.parent.mkdir()
    g.write_text("placeholder")
    assert audit_paths([g])
    assert len(application_routes()) == 81 and audit_routes() == []
    assert (
        "quality: incident-response-review incident-runbook audit-log-boundary-map "
        "forensics-evidence-checklist"
        in (ROOT / "Makefile").read_text()
    )
