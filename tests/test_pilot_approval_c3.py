import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.pilot_approval import PilotApprovalPacket, PilotApprovalStatus
from app.services.pilot_approval import (
    PilotApprovalBlockedError,
    build_fake_pilot_approval_template,
    build_pilot_approval_validation_report,
    evaluate_pilot_approval_packet,
    validate_pilot_approval_packet,
    write_pilot_approval_artifacts,
)

EXAMPLE = Path("examples/pilot-approval/example_pilot_approval_packet.json")


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load_example() -> PilotApprovalPacket:
    return PilotApprovalPacket.model_validate_json(EXAMPLE.read_text())


def updated(**values) -> PilotApprovalPacket:
    data = load_example().model_dump(mode="json")
    data.update(values)
    return PilotApprovalPacket.model_validate(data)


def signoff_updated(**values) -> PilotApprovalPacket:
    data = load_example().model_dump(mode="json")
    data["signoff_placeholders"][0].update(values)
    return PilotApprovalPacket.model_validate(data)


def blocking_codes(packet: PilotApprovalPacket) -> set[str]:
    return {
        finding.code
        for finding in validate_pilot_approval_packet(packet, configured())
        if finding.severity == "blocking"
    }


def finding_codes(packet: PilotApprovalPacket) -> set[str]:
    return {
        finding.code
        for finding in validate_pilot_approval_packet(packet, configured())
    }


def complete_packet(*, approved: bool = False) -> PilotApprovalPacket:
    data = load_example().model_dump(mode="json")
    data["readiness"]["pilot_readiness_decision_status"] = "GO"
    data["known_limitations"][0]["status"] = "ready_for_private_review"
    data["risk_acceptance"][0]["acceptance_status"] = "ready_for_private_review"
    if approved:
        data["approval_decision"] = "approved_placeholder"
        data["approval_status"] = "approved_placeholder"
        data["signoff_placeholders"][0]["decision"] = "approved_placeholder"
    return PilotApprovalPacket.model_validate(data)


def test_fake_example_and_generated_template_validate_safely():
    for packet in (load_example(), build_fake_pilot_approval_template()):
        report = build_pilot_approval_validation_report(packet, configured())
        assert report.blocking_findings_count == 0
        assert report.evaluation == PilotApprovalStatus.NEEDS_REVIEW
        assert report.external_calls is False
        assert report.procore_calls is False
        assert report.approved_real_pilot is False
        assert report.file_contents_read is False


@pytest.mark.parametrize(
    ("packet", "code"),
    [
        (signoff_updated(reviewer_placeholder="Named Reviewer"), "real_identity"),
        (signoff_updated(approver_placeholder="Named Approver"), "real_identity"),
        (updated(generated_by_placeholder="Named Operator"), "real_identity"),
        (updated(approval_notes=["reviewer@customer-build.com"]), "email"),
        (updated(approval_notes=["312-555-0199"]), "phone"),
        (updated(approval_notes=["Procore project 87654321"]), "real_id"),
        (updated(approval_notes=["customer-build.com"]), "domain"),
        (updated(approval_notes=["client_secret=fake-private-value"]), "secret"),
        (
            updated(approval_notes=["Authorization: Bearer fake-private-value"]),
            "secret",
        ),
        (
            updated(
                approval_notes=[
                    "https://files.invalid/object?signature=fake-private-value"
                ]
            ),
            "signed_url",
        ),
        (updated(approval_notes=["/Users/operator/private/approval.json"]), "absolute_path"),
        (updated(approval_notes=["PRIVATE_TOKEN=fake-private-value"]), "env_assignment"),
        (
            updated(
                approval_notes=[
                    "postgresql://operator:placeholder@database.invalid/pilot"
                ]
            ),
            "database_url",
        ),
        (updated(approval_notes=["s3://private-customer-bucket/approval"]), "storage_url"),
        (updated(approval_notes=["raw payload: {project: placeholder}"]), "raw_content"),
        (updated(approval_notes=["raw support bundle contents"]), "raw_content"),
        (updated(approval_notes=["raw smoke report contents"]), "raw_content"),
        (updated(approval_notes=["raw webhook report contents"]), "raw_content"),
        (updated(approval_notes=["raw evidence contents"]), "raw_content"),
        (
            updated(approval_notes=["raw evidence review artifacts"]),
            "raw_content",
        ),
        (
            updated(approval_notes=["PRIVATE_PACKET_REF_PLACEHOLDER/packet.pdf"]),
            "binary_reference",
        ),
        (
            updated(
                approval_notes=[
                    "PRIVATE_PACKET_REF_PLACEHOLDER/report.pilot-approval-packet.json"
                ]
            ),
            "binary_reference",
        ),
    ],
)
def test_unsafe_packet_values_are_blocked(packet, code):
    assert code in blocking_codes(packet)
    assert (
        evaluate_pilot_approval_packet(packet, configured())
        == PilotApprovalStatus.BLOCKED
    )


def test_raw_payload_like_extra_field_is_rejected_by_schema():
    data = load_example().model_dump(mode="json")
    data["raw_payload"] = {"project": {"id": "PROJECT_ID_PLACEHOLDER"}}
    with pytest.raises(ValueError):
        PilotApprovalPacket.model_validate(data)


def test_excessive_approvers_and_conditions_are_blocked():
    data = load_example().model_dump(mode="json")
    data["signoff_placeholders"] *= 11
    assert "max_approvers" in blocking_codes(PilotApprovalPacket.model_validate(data))
    data = load_example().model_dump(mode="json")
    data["launch_conditions"] *= 51
    assert "max_conditions" in blocking_codes(PilotApprovalPacket.model_validate(data))
    data = load_example().model_dump(mode="json")
    data["rollback_conditions"] *= 51
    assert "max_conditions" in blocking_codes(PilotApprovalPacket.model_validate(data))


def test_non_placeholder_approver_and_production_are_blocked():
    assert "identity_placeholder" in blocking_codes(
        updated(approved_by_placeholders=["Private Approval Team"])
    )
    assert "production_packet" in blocking_codes(updated(environment="production"))


@pytest.mark.parametrize("readiness", ["NO_GO", "BLOCKED"])
def test_placeholder_approval_cannot_override_readiness(readiness):
    data = complete_packet(approved=True).model_dump(mode="json")
    data["readiness"]["pilot_readiness_decision_status"] = readiness
    packet = PilotApprovalPacket.model_validate(data)
    assert "approval_readiness" in finding_codes(packet)
    assert evaluate_pilot_approval_packet(packet, configured()) == PilotApprovalStatus.NEEDS_REVIEW


def test_expired_evidence_and_renewal_block_placeholder_approval():
    data = complete_packet(approved=True).model_dump(mode="json")
    data["review"]["expired_evidence_count"] = 1
    expired = PilotApprovalPacket.model_validate(data)
    assert "expired_evidence" in finding_codes(expired)
    assert evaluate_pilot_approval_packet(expired, configured()) == PilotApprovalStatus.NEEDS_REVIEW

    data = complete_packet(approved=True).model_dump(mode="json")
    data["review"]["renewal_required_count"] = 1
    data["known_limitations"] = []
    data["risk_acceptance"] = []
    renewal = PilotApprovalPacket.model_validate(data)
    assert "renewal_acceptance" in finding_codes(renewal)
    assert evaluate_pilot_approval_packet(renewal, configured()) == PilotApprovalStatus.NEEDS_REVIEW


@pytest.mark.parametrize(
    ("updates", "code"),
    [
        ({"launch_conditions": []}, "launch_conditions"),
        ({"rollback_conditions": []}, "rollback_conditions"),
        ({"known_limitations": []}, "known_limitations"),
        ({"signoff_placeholders": []}, "signoff_placeholders"),
    ],
)
def test_missing_required_sections_need_review(updates, code):
    packet = updated(**updates)
    assert code in finding_codes(packet)
    assert evaluate_pilot_approval_packet(packet, configured()) == PilotApprovalStatus.NEEDS_REVIEW


def test_missing_risk_acceptance_needs_review():
    packet = updated(risk_acceptance=[])
    assert "risk_acceptance" in finding_codes(packet)
    assert evaluate_pilot_approval_packet(packet, configured()) == PilotApprovalStatus.NEEDS_REVIEW


def test_evaluation_states():
    assert (
        evaluate_pilot_approval_packet(load_example(), configured())
        == PilotApprovalStatus.NEEDS_REVIEW
    )
    assert (
        evaluate_pilot_approval_packet(complete_packet(), configured())
        == PilotApprovalStatus.READY_FOR_PRIVATE_REVIEW
    )
    assert (
        evaluate_pilot_approval_packet(complete_packet(approved=True), configured())
        == PilotApprovalStatus.APPROVED_PLACEHOLDER
    )
    assert (
        evaluate_pilot_approval_packet(
            updated(approval_decision="rejected_placeholder"), configured()
        )
        == PilotApprovalStatus.REJECTED_PLACEHOLDER
    )
    assert (
        evaluate_pilot_approval_packet(
            load_example(), configured(pilot_approval_packet_enabled=False)
        )
        == PilotApprovalStatus.BLOCKED
    )


def test_artifacts_generate_only_under_output_root(tmp_path):
    root = tmp_path / "pilot-approval-output"
    result = write_pilot_approval_artifacts(load_example(), root, configured())
    target = root / result.output_directory
    assert target.parent == root
    assert set(result.files) == {path.name for path in target.iterdir()}
    assert set(result.files) == {
        "approval-packet.json",
        "approval-packet.md",
        "approval-summary.md",
        "launch-conditions.md",
        "rollback-conditions.md",
        "risk-acceptance.md",
        "signoff-template.md",
        "manifest.json",
    }
    contents = "\n".join(path.read_text() for path in target.iterdir())
    assert "Bearer fake" not in contents
    assert "?signature=" not in contents
    assert "/Users/" not in contents
    assert str(tmp_path) not in contents
    assert result.external_calls is False
    assert result.approved_real_pilot is False
    assert result.file_contents_included is False


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_artifact_path_traversal_is_blocked(root):
    with pytest.raises(PilotApprovalBlockedError):
        write_pilot_approval_artifacts(load_example(), root, configured())


def test_unsafe_packet_is_not_written(tmp_path):
    root = tmp_path / "pilot-approval-output"
    with pytest.raises(PilotApprovalBlockedError):
        write_pilot_approval_artifacts(
            updated(approval_notes=["Authorization: Bearer fake-private-value"]),
            root,
            configured(),
        )
    assert not root.exists()


def test_safety_checker_passes_example_and_generated_packet(tmp_path):
    example = subprocess.run(
        [sys.executable, "scripts/check_pilot_approval_safety.py", str(EXAMPLE)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "passed" in example.stdout
    root = tmp_path / "pilot-approval-output"
    write_pilot_approval_artifacts(load_example(), root, configured())
    generated = subprocess.run(
        [sys.executable, "scripts/check_pilot_approval_safety.py", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "passed" in generated.stdout


def test_safety_checker_fails_unsafe_file_without_leaking(tmp_path):
    secret = "must-not-appear-approval-secret"
    unsafe = tmp_path / "unsafe.json"
    unsafe.write_text(json.dumps({"authorization": f"Bearer {secret}"}))
    result = subprocess.run(
        [sys.executable, "scripts/check_pilot_approval_safety.py", str(unsafe)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert secret not in result.stdout


def test_safety_checker_fails_unsafe_generated_artifact_without_leaking(tmp_path):
    secret = "must-not-appear-generated-approval-secret"
    root = tmp_path / "pilot-approval-output"
    result = write_pilot_approval_artifacts(load_example(), root, configured())
    target = root / result.output_directory / "approval-summary.md"
    target.write_text(f"Authorization: Bearer {secret}")
    checked = subprocess.run(
        [sys.executable, "scripts/check_pilot_approval_safety.py", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 1
    assert secret not in checked.stdout


def test_cli_template_validation_and_generation(tmp_path):
    template = subprocess.run(
        [sys.executable, "scripts/print_pilot_approval_template.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Example Pilot Approval Packet" in template.stdout
    validation = subprocess.run(
        [sys.executable, "scripts/validate_pilot_approval_packet.py", str(EXAMPLE)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"evaluation": "needs_review"' in validation.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_approval_packet.py",
            str(EXAMPLE),
            "--output-root",
            str(tmp_path / "pilot-approval-output"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(tmp_path) not in generated.stdout
    assert '"external_calls": false' in generated.stdout


def test_cli_strict_modes_and_traversal(tmp_path):
    secret = "must-not-appear-approval-credential"
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text(
        json.dumps(
            updated(
                approval_notes=[f"Authorization: Bearer {secret}"]
            ).model_dump(mode="json")
        )
    )
    strict = subprocess.run(
        [
            sys.executable,
            "scripts/validate_pilot_approval_packet.py",
            str(blocked_path),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
    assert secret not in strict.stdout
    review = subprocess.run(
        [
            sys.executable,
            "scripts/validate_pilot_approval_packet.py",
            str(EXAMPLE),
            "--strict-review",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert review.returncode == 1
    traversal = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_approval_packet.py",
            str(EXAMPLE),
            "--output-root",
            "../unsafe-approval-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert traversal.returncode == 2
    assert "unsafe output root" in traversal.stdout


def test_docs_and_example_state_public_boundaries():
    docs = Path("docs/pilot-approval-packet.md").read_text().casefold()
    readme = Path("README.md").read_text().casefold()
    examples = Path("examples/pilot-approval/README.md").read_text().casefold()
    assert "no real approval" in docs
    assert "no procore calls" in docs
    assert "fake examples only" in docs
    assert "generated artifacts are ignored" in docs
    assert "not legal or compliance approval" in docs
    assert "phase c3" in readme
    assert "must never be committed" in examples


def test_no_c3_api_route_or_external_automation():
    route_sources = "\n".join(path.read_text() for path in Path("app/api").rglob("*.py"))
    assert "/pilot-approval" not in route_sources
    assert not Path(".github/workflows/pilot-approval.yml").exists()
