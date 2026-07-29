import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.evidence_review import (
    EvidenceExpiryStatus,
    EvidenceReviewManifest,
)
from app.services.evidence_review import (
    EvidenceReviewBlockedError,
    build_evidence_review_report,
    build_fake_evidence_review_template,
    calculate_expiry_status,
    validate_evidence_review_manifest,
    write_evidence_review_artifacts,
)

EXAMPLE = Path("examples/evidence-review/example_evidence_review_manifest.json")


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load_example() -> EvidenceReviewManifest:
    return EvidenceReviewManifest.model_validate_json(EXAMPLE.read_text())


def updated(**values) -> EvidenceReviewManifest:
    data = load_example().model_dump(mode="json")
    data.update(values)
    return EvidenceReviewManifest.model_validate(data)


def item_updated(index: int = 0, **values) -> EvidenceReviewManifest:
    data = load_example().model_dump(mode="json")
    data["review_items"][index].update(values)
    return EvidenceReviewManifest.model_validate(data)


def reviewer_updated(**values) -> EvidenceReviewManifest:
    data = load_example().model_dump(mode="json")
    data["review_items"][0]["reviewer_placeholder"].update(values)
    return EvidenceReviewManifest.model_validate(data)


def blocking_codes(manifest: EvidenceReviewManifest) -> set[str]:
    return {
        finding.code
        for finding in validate_evidence_review_manifest(manifest, configured())
        if finding.severity == "blocking"
    }


def test_fake_example_and_generated_template_validate():
    for manifest in (load_example(), build_fake_evidence_review_template()):
        report = build_evidence_review_report(manifest, configured())
        assert report.valid is True
        assert report.blocking_findings_count == 0
        assert report.summary.needs_review_items >= 1
        assert report.summary.expires_soon_items >= 1
        assert report.summary.renewal_required_items >= 1
        assert report.external_calls is False
        assert report.notifications_sent is False
        assert report.file_contents_read is False


@pytest.mark.parametrize(
    ("manifest", "code"),
    [
        (reviewer_updated(reviewer_placeholder="Named Reviewer"), "real_identity"),
        (reviewer_updated(approver_placeholder="Named Approver"), "real_identity"),
        (updated(notes=["reviewer@customer-build.com"]), "email"),
        (updated(notes=["312-555-0199"]), "phone"),
        (updated(notes=["Procore project 87654321"]), "real_id"),
        (updated(notes=["customer-build.com"]), "domain"),
        (updated(notes=["client_secret=fake-private-value"]), "secret"),
        (updated(notes=["Authorization: Bearer fake-private-value"]), "secret"),
        (
            updated(notes=["https://files.invalid/object?signature=fake-value"]),
            "signed_url",
        ),
        (updated(notes=["/Users/operator/private/review.json"]), "absolute_path"),
        (updated(notes=["PRIVATE_TOKEN=fake-private-value"]), "env_assignment"),
        (
            updated(notes=["postgresql://operator:placeholder@database.invalid/pilot"]),
            "database_url",
        ),
        (updated(notes=["s3://private-customer-bucket/review"]), "storage_url"),
        (updated(notes=["raw payload: {project: placeholder}"]), "raw_report"),
        (updated(notes=["raw support bundle contents"]), "raw_report"),
        (updated(notes=["raw smoke report contents"]), "raw_report"),
        (updated(notes=["raw webhook report contents"]), "raw_report"),
        (updated(notes=["PRIVATE_REVIEW_REF_PLACEHOLDER/review.pdf"]), "binary_reference"),
        (
            updated(notes=["PRIVATE_REVIEW_REF_PLACEHOLDER/report.evidence-review.json"]),
            "binary_reference",
        ),
    ],
)
def test_unsafe_review_values_are_blocked(manifest, code):
    assert code in blocking_codes(manifest)


def test_raw_payload_like_extra_field_is_rejected_by_schema():
    data = load_example().model_dump(mode="json")
    data["raw_payload"] = {"project": {"id": "PROJECT_ID_PLACEHOLDER"}}
    with pytest.raises(ValueError):
        EvidenceReviewManifest.model_validate(data)


def test_excessive_items_are_blocked():
    data = load_example().model_dump(mode="json")
    data["review_items"] *= 21
    assert "max_items" in blocking_codes(EvidenceReviewManifest.model_validate(data))


def test_non_placeholder_review_owner_is_blocked():
    assert "identity_placeholder" in blocking_codes(
        updated(review_owner_placeholder="Review Team")
    )


def test_expiry_beyond_maximum_is_blocked():
    manifest = item_updated(
        reviewed_at_placeholder="2026-01-01T00:00:00Z",
        expires_at_placeholder="2026-05-01T00:00:00Z",
    )
    assert "expiry_window" in blocking_codes(manifest)


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("reviewed_at_placeholder", "accepted_review_time"),
        ("expires_at_placeholder", "accepted_expiry_time"),
    ],
)
def test_accepted_evidence_requires_timestamp_placeholders(field, code):
    assert code in blocking_codes(item_updated(**{field: ""}))


def test_expired_accepted_evidence_requires_renewal():
    manifest = item_updated(
        reviewed_at_placeholder="2025-01-01T00:00:00Z",
        expires_at_placeholder="2025-01-31T00:00:00Z",
        renewal_required=False,
    )
    assert "expired_accepted" in blocking_codes(manifest)


def test_production_profile_is_blocked_by_safe_defaults():
    assert "production_profile" in blocking_codes(updated(environment="production"))


def test_expiry_calculation_states():
    settings = configured(evidence_review_warn_within_days=7)
    now = datetime(2026, 1, 15, tzinfo=UTC)
    assert (
        calculate_expiry_status("", "", settings, now=now)
        == EvidenceExpiryStatus.NEEDS_REVIEW
    )
    assert (
        calculate_expiry_status("REVIEWED_AT_PLACEHOLDER", "", settings, now=now)
        == EvidenceExpiryStatus.NEEDS_REVIEW
    )
    assert (
        calculate_expiry_status(
            "2026-01-01T00:00:00Z", "2026-02-15T00:00:00Z", settings, now=now
        )
        == EvidenceExpiryStatus.CURRENT
    )
    assert (
        calculate_expiry_status(
            "2026-01-01T00:00:00Z", "2026-01-20T00:00:00Z", settings, now=now
        )
        == EvidenceExpiryStatus.EXPIRES_SOON
    )
    assert (
        calculate_expiry_status(
            "2025-12-01T00:00:00Z", "2026-01-14T00:00:00Z", settings, now=now
        )
        == EvidenceExpiryStatus.EXPIRED
    )


def test_renewal_and_not_applicable_gate_behavior():
    report = build_evidence_review_report(load_example(), configured())
    renewal = next(g for g in report.gates if g.renewal_required)
    not_applicable = next(
        g for g in report.gates if g.review_status.value == "not_applicable"
    )
    assert renewal.expiry_status == EvidenceExpiryStatus.RENEWAL_REQUIRED
    assert renewal.blocks_gate is True
    assert not_applicable.blocks_gate is False


def test_artifacts_generate_only_under_output_root(tmp_path):
    root = tmp_path / "evidence-review-output"
    result = write_evidence_review_artifacts(load_example(), root, configured())
    target = root / result.output_directory
    assert target.parent == root
    assert set(result.files) == {path.name for path in target.iterdir()}
    assert set(result.files) == {
        "review-summary.md",
        "expiry-report.json",
        "renewal-checklist.md",
        "signoff-template.md",
        "review-manifest.template.json",
        "manifest.json",
    }
    contents = "\n".join(path.read_text() for path in target.iterdir())
    assert "Bearer fake" not in contents
    assert "?signature=" not in contents
    assert "/Users/" not in contents
    assert str(tmp_path) not in contents
    assert result.external_calls is False
    assert result.notifications_sent is False
    assert result.file_contents_included is False


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_artifact_path_traversal_is_blocked(root):
    with pytest.raises(EvidenceReviewBlockedError):
        write_evidence_review_artifacts(load_example(), root, configured())


def test_unsafe_review_is_not_written(tmp_path):
    root = tmp_path / "evidence-review-output"
    with pytest.raises(EvidenceReviewBlockedError):
        write_evidence_review_artifacts(
            updated(notes=["Authorization: Bearer fake-private-value"]),
            root,
            configured(),
        )
    assert not root.exists()


def test_cli_template_validation_expiry_and_generation(tmp_path):
    template = subprocess.run(
        [sys.executable, "scripts/print_evidence_review_template.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Example Evidence Review" in template.stdout
    validation = subprocess.run(
        [sys.executable, "scripts/validate_evidence_review.py", str(EXAMPLE)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"valid": true' in validation.stdout
    expiry = subprocess.run(
        [sys.executable, "scripts/check_evidence_expiry.py", str(EXAMPLE)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"notifications_sent": false' in expiry.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_evidence_review_artifacts.py",
            str(EXAMPLE),
            "--output-root",
            str(tmp_path / "evidence-review-output"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(tmp_path) not in generated.stdout
    assert '"external_calls": false' in generated.stdout


def test_cli_strict_modes_fail_safely(tmp_path):
    secret = "must-not-appear-review-credential"
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text(
        json.dumps(updated(notes=[f"Authorization: Bearer {secret}"]).model_dump(mode="json"))
    )
    strict = subprocess.run(
        [
            sys.executable,
            "scripts/validate_evidence_review.py",
            str(blocked_path),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
    assert secret not in strict.stdout
    strict_review = subprocess.run(
        [
            sys.executable,
            "scripts/validate_evidence_review.py",
            str(EXAMPLE),
            "--strict-review",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict_review.returncode == 1
    expiry = subprocess.run(
        [
            sys.executable,
            "scripts/check_evidence_expiry.py",
            str(EXAMPLE),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert expiry.returncode == 1


def test_generate_cli_rejects_output_root_traversal():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_evidence_review_artifacts.py",
            str(EXAMPLE),
            "--output-root",
            "../unsafe-review-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unsafe output root" in result.stdout


def test_docs_and_public_examples_state_boundaries():
    docs = Path("docs/evidence-review-expiry.md").read_text().casefold()
    readme = Path("README.md").read_text().casefold()
    examples = Path("examples/evidence-review/README.md").read_text().casefold()
    assert "no real review or signoff" in docs
    assert "no procore calls" in docs
    assert "fake examples only" in docs
    assert "generated artifacts are ignored" in docs
    assert "phase c2" in readme
    assert "must never be committed" in examples


def test_no_c2_api_route_or_notification_integration():
    route_sources = "\n".join(path.read_text() for path in Path("app/api").rglob("*.py"))
    assert "/evidence-review" not in route_sources
    assert not Path(".github/workflows/evidence-review.yml").exists()
    assert not any(
        path.name in {"slack.py", "sms.py", "email.py", "calendar.py"}
        for path in Path("app").rglob("*.py")
    )
