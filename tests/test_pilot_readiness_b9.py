import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.pilot_readiness import (
    PilotReadinessDecision,
    PilotReadinessProfile,
)
from app.services.pilot_readiness import (
    PilotReadinessBlockedError,
    build_pilot_readiness_report,
    evaluate_pilot_gate,
    validate_pilot_readiness_profile,
    write_pilot_readiness_artifacts,
)

EXAMPLE = Path("examples/pilot-readiness/example_pilot_profile.json")


def configured(**values):
    return Settings(_env_file=None, **values)


def load_example() -> PilotReadinessProfile:
    return PilotReadinessProfile.model_validate_json(EXAMPLE.read_text())


def updated(**values) -> PilotReadinessProfile:
    data = load_example().model_dump(mode="json")
    data.update(values)
    return PilotReadinessProfile.model_validate(data)


def blocking_codes(profile, settings=None):
    return {
        finding.code
        for finding in validate_pilot_readiness_profile(
            profile, settings or configured()
        )
        if finding.severity == "blocking"
    }


def test_fake_example_is_safe_and_needs_review():
    report = build_pilot_readiness_report(load_example(), configured())
    assert report.decision == PilotReadinessDecision.NEEDS_REVIEW
    assert report.blocking_count == 0
    assert report.external_calls is False
    assert report.procore_calls is False
    assert report.deployed is False


def test_complete_fake_profile_can_return_go():
    profile = updated(monitoring_plan_status="passed", known_limitations=[])
    assert evaluate_pilot_gate(profile, configured()) == PilotReadinessDecision.GO


@pytest.mark.parametrize(
    "updates, code",
    [
        ({"company_id": "123456"}, "real_id"),
        ({"public_base_url": "https://real-customer.example.com"}, "domain_placeholder"),
        ({"notes": ["Authorization: Bearer fake-pilot-token"]}, "sensitive_value"),
        ({"notes": ["webhook_secret=fake-secret-value"]}, "sensitive_value"),
        (
            {"notes": ["https://example.invalid/file?signature=fake-signature"]},
            "signed_url",
        ),
        ({"notes": ["/Users/example/private/pilot.json"]}, "private_path"),
        ({"notes": ["support-output/private-report.json"]}, "private_output"),
    ],
)
def test_real_or_private_material_is_blocked(updates, code):
    profile = updated(**updates)
    assert code in blocking_codes(profile)
    assert evaluate_pilot_gate(profile, configured()) == PilotReadinessDecision.BLOCKED


def test_disabled_and_production_profiles_are_blocked():
    assert evaluate_pilot_gate(
        load_example(), configured(pilot_readiness_enabled=False)
    ) == PilotReadinessDecision.BLOCKED
    assert evaluate_pilot_gate(
        updated(environment="production"), configured()
    ) == PilotReadinessDecision.BLOCKED


@pytest.mark.parametrize(
    "updates, code",
    [
        ({"admin_auth_mode": "local_optional"}, "admin_auth"),
        ({"sandbox_smoke_status": "missing", "sandbox_smoke_report_ref": ""}, "sandbox_smoke"),
        ({"dmsa_onboarding_status": "missing", "dmsa_onboarding_ref": ""}, "dmsa_onboarding"),
        ({"migration_safety_status": "missing", "migration_safety_ref": ""}, "migration_safety"),
        ({"storage_review_status": "missing", "storage_review_ref": ""}, "storage_review"),
        (
            {"support_diagnostics_status": "missing", "support_diagnostics_ref": ""},
            "support_diagnostics",
        ),
        ({"rollback_plan_status": "missing", "rollback_plan_ref": ""}, "rollback_plan"),
        (
            {"secret_provider_kind": "external_placeholder"},
            "secret_provider",
        ),
        (
            {"storage_provider_kind": "external_placeholder"},
            "storage_provider",
        ),
        ({"database_profile": "sqlite-local"}, "pilot_database"),
    ],
)
def test_required_pilot_evidence_and_posture_block(updates, code):
    profile = updated(**updates)
    assert code in blocking_codes(profile)
    assert evaluate_pilot_gate(profile, configured()) == PilotReadinessDecision.NO_GO


def test_webhook_review_is_required_only_when_planned():
    profile = updated(
        webhooks_planned=True,
        webhook_docs_status="needs_review",
        webhook_signature_status="missing",
        webhook_verification_status="missing",
        webhook_verification_ref="",
    )
    assert "webhook_review" in blocking_codes(profile)
    assert evaluate_pilot_gate(profile, configured()) == PilotReadinessDecision.NO_GO


def test_missing_operator_approval_is_no_go():
    approval = load_example().internal_approval_placeholder.model_dump(mode="json")
    approval.update({"status": "missing", "evidence_ref": ""})
    profile = updated(internal_approval_placeholder=approval)
    assert "operator_approval" in blocking_codes(profile)
    assert evaluate_pilot_gate(profile, configured()) == PilotReadinessDecision.NO_GO


def test_local_dry_run_can_mark_sandbox_smoke_not_applicable():
    profile = updated(
        environment="local",
        local_only_dry_run=True,
        database_profile="sqlite-local",
        sandbox_smoke_status="not_applicable",
        sandbox_smoke_report_ref="",
        monitoring_plan_status="passed",
        known_limitations=[],
    )
    assert "sandbox_smoke" not in blocking_codes(profile)
    assert "pilot_database" not in blocking_codes(profile)


def test_artifacts_generate_only_under_safe_root(tmp_path):
    result = write_pilot_readiness_artifacts(
        load_example(), tmp_path / "pilot-readiness-output", configured()
    )
    directory = tmp_path / "pilot-readiness-output" / result.output_directory
    assert len(result.files) == 6
    assert {item.name for item in directory.iterdir()} == set(result.files)
    contents = "\n".join(item.read_text() for item in directory.iterdir())
    assert "Bearer " not in contents
    assert "?signature=" not in contents
    assert "/Users/" not in contents
    assert "support-output/" not in contents
    assert result.external_calls is False


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_artifact_path_traversal_is_blocked(root):
    with pytest.raises(PilotReadinessBlockedError):
        write_pilot_readiness_artifacts(load_example(), root, configured())


def test_no_go_artifacts_fail_closed(tmp_path):
    with pytest.raises(PilotReadinessBlockedError):
        write_pilot_readiness_artifacts(
            updated(database_profile="sqlite-local"), tmp_path / "output", configured()
        )


def test_cli_template_validation_and_generation(tmp_path):
    template = subprocess.run(
        [sys.executable, "scripts/print_pilot_readiness_template.py"],
        check=True, capture_output=True, text=True,
    )
    assert "Example Pilot" in template.stdout
    validation = subprocess.run(
        [sys.executable, "scripts/validate_pilot_readiness.py", str(EXAMPLE)],
        check=True, capture_output=True, text=True,
    )
    assert '"decision": "NEEDS_REVIEW"' in validation.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_readiness_artifacts.py",
            str(EXAMPLE),
            "--output-root",
            str(tmp_path / "generated"),
        ],
        check=True, capture_output=True, text=True,
    )
    assert str(tmp_path) not in generated.stdout
    assert '"external_calls": false' in generated.stdout


def test_cli_strict_modes_and_traversal(tmp_path):
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text(json.dumps(updated(database_profile="sqlite-local").model_dump(
        mode="json"
    )))
    strict = subprocess.run(
        [
            sys.executable,
            "scripts/validate_pilot_readiness.py",
            str(blocked_path),
            "--strict",
        ],
        check=False, capture_output=True, text=True,
    )
    assert strict.returncode == 1
    review = subprocess.run(
        [
            sys.executable,
            "scripts/validate_pilot_readiness.py",
            str(EXAMPLE),
            "--strict-review",
        ],
        check=False, capture_output=True, text=True,
    )
    assert review.returncode == 1
    traversal = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_readiness_artifacts.py",
            str(EXAMPLE),
            "--output-root",
            "../unsafe-pilot-output",
        ],
        check=False, capture_output=True, text=True,
    )
    assert traversal.returncode == 2


def test_docs_and_example_disclaim_real_approval():
    docs = Path("docs/pilot-readiness-gate.md").read_text().casefold()
    example_docs = Path("examples/pilot-readiness/README.md").read_text().casefold()
    readme = Path("README.md").read_text().casefold()
    assert "no deployment automation" in docs
    assert "no procore calls" in docs
    assert "not production deployment approval" in docs
    assert "must never be committed" in example_docs
    assert "pilot" in readme
    assert "not automatically approved" in readme
