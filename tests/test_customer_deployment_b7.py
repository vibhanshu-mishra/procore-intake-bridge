import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.customer_deployment import CustomerDeploymentProfile
from app.services.customer_deployment import (
    CustomerDeploymentBlockedError,
    build_customer_deployment_readiness_report,
    validate_customer_deployment_profile,
    write_customer_deployment_artifacts,
)

EXAMPLE = Path("examples/customer-deployments/example_customer_profile.json")


def configured(**values):
    return Settings(_env_file=None, **values)


def load_example() -> CustomerDeploymentProfile:
    return CustomerDeploymentProfile.model_validate_json(EXAMPLE.read_text())


def production_profile(**updates) -> CustomerDeploymentProfile:
    data = load_example().model_dump()
    data.update({
        "environment": "production",
        "secret_provider": "managed_reference",
        "storage_provider": "managed_reference",
        "database_profile": "MANAGED_DATABASE_PROFILE_PLACEHOLDER",
        "migration_plan": "MIGRATION_PLAN_PLACEHOLDER",
        "backup_plan": "BACKUP_PLAN_PLACEHOLDER",
        "rollback_plan": "ROLLBACK_PLAN_PLACEHOLDER",
        "sandbox_smoke_result_ref": "SANITIZED_SMOKE_RESULT_REF_PLACEHOLDER",
        "onboarding_packet_ref": "ONBOARDING_PACKET_REF_PLACEHOLDER",
        "admin_auth_plan": {
            "mode": "token_required",
            "token_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_TOKEN",
            "rotation_token_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_ROTATION_TOKEN",
        },
    })
    data.update(updates)
    return CustomerDeploymentProfile.model_validate(data)


def codes(profile, settings=None):
    return {
        finding.code
        for finding in validate_customer_deployment_profile(
            profile, settings or configured()
        )
        if finding.severity == "blocking"
    }


def test_fake_example_profile_validates_for_staging():
    report = build_customer_deployment_readiness_report(load_example(), configured())
    assert report.ready is True
    assert report.external_calls is False
    assert report.deployed is False


def test_real_looking_ids_and_domain_are_blocked():
    data = load_example().model_dump()
    data["requested_project_scopes"][0]["project_id"] = "123456"
    data["public_base_url"] = "https://customer-corp.com"
    data["allowed_hosts"] = ["customer-corp.com"]
    blocked = codes(CustomerDeploymentProfile.model_validate(data))
    assert {"real_id", "project_placeholder", "public_url", "host_placeholder"} <= blocked


@pytest.mark.parametrize(
    "note, expected",
    [
        ("Authorization: Bearer fake-token-value", "secret_value"),
        ("webhook_secret=fake-secret-value", "secret_value"),
        ("https://example.invalid/file?signature=fake-signature-value", "signed_url"),
        ("/Users/private/customer/file.json", "private_path"),
    ],
)
def test_sensitive_values_urls_and_paths_are_blocked(note, expected):
    data = load_example().model_dump()
    data["notes"] = [note]
    assert expected in codes(CustomerDeploymentProfile.model_validate(data))


def test_project_count_cap_is_enforced():
    data = load_example().model_dump()
    data["requested_project_scopes"] *= 2
    profile = CustomerDeploymentProfile.model_validate(data)
    assert "project_cap" in codes(profile, configured(customer_profile_max_projects=1))


@pytest.mark.parametrize(
    "updates, expected",
    [
        ({"allowed_hosts": ["*"]}, "wildcard_host"),
        ({"database_profile": "sqlite-local"}, "database"),
        ({"secret_provider": "external_placeholder"}, "secret_provider"),
        ({"storage_provider": "external_placeholder"}, "storage_provider"),
        ({"migration_plan": ""}, "migration_plan"),
        ({"backup_plan": ""}, "recovery_plan"),
        ({"rollback_plan": ""}, "recovery_plan"),
        ({"onboarding_packet_ref": ""}, "onboarding_packet"),
        ({"sandbox_smoke_result_ref": ""}, "sandbox_smoke"),
        (
            {"admin_auth_plan": {"mode": "local_optional", "token_ref": "",
                                 "rotation_token_ref": ""}},
            "admin_auth",
        ),
    ],
)
def test_production_requirements_block_incomplete_plans(updates, expected):
    assert expected in codes(production_profile(**updates))


def test_production_webhook_dependencies_are_required():
    plan = deepcopy(load_example().webhook_plan.model_dump())
    plan.update({
        "enabled": True,
        "signature_required": False,
        "docs_verification_status": "needs_review",
    })
    blocked = codes(production_profile(webhook_secret_ref="", webhook_plan=plan))
    assert {"webhook_signature", "webhook_verification"} <= blocked


def test_fake_artifacts_are_safely_generated_under_temp_root(tmp_path):
    result = write_customer_deployment_artifacts(
        load_example(), tmp_path / "customer-output", configured()
    )
    assert result.output_directory == "example-customer-staging"
    root = tmp_path / "customer-output" / result.output_directory
    assert len(result.files) == 6
    contents = "\n".join((root / name).read_text() for name in result.files).casefold()
    assert "bearer " not in contents
    assert "?signature=" not in contents
    assert "/users/" not in contents
    assert result.secrets_included is False


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_artifact_output_path_traversal_is_blocked(root):
    with pytest.raises(CustomerDeploymentBlockedError):
        write_customer_deployment_artifacts(load_example(), root, configured())


def test_fail_closed_artifact_generation_refuses_blocked_profile(tmp_path):
    with pytest.raises(CustomerDeploymentBlockedError):
        write_customer_deployment_artifacts(
            production_profile(database_profile="sqlite-local"),
            tmp_path / "output",
            configured(),
        )


def test_customer_cli_tools_are_offline_and_sanitized(tmp_path):
    template = subprocess.run(
        [sys.executable, "scripts/print_customer_deployment_template.py"],
        check=True, capture_output=True, text=True,
    )
    assert "Example Customer" in template.stdout
    validation = subprocess.run(
        [sys.executable, "scripts/validate_customer_deployment_profile.py", str(EXAMPLE)],
        check=True, capture_output=True, text=True,
    )
    assert '"external_calls": false' in validation.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_customer_deployment_artifacts.py",
            str(EXAMPLE),
            "--output-root",
            str(tmp_path / "generated"),
        ],
        check=True, capture_output=True, text=True,
    )
    assert str(tmp_path) not in generated.stdout
    assert '"secrets_included": false' in generated.stdout


def test_validate_cli_strict_returns_nonzero_for_blockers(tmp_path):
    path = tmp_path / "blocked.json"
    data = production_profile(database_profile="sqlite-local").model_dump(mode="json")
    path.write_text(json.dumps(data))
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_customer_deployment_profile.py",
            str(path),
            "--strict",
        ],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "sqlite" in result.stdout.casefold()


def test_documentation_and_examples_state_safety_boundaries():
    docs = Path("docs/customer-deployment-pattern.md").read_text().casefold()
    readme = Path("README.md").read_text().casefold()
    examples = Path("examples/customer-deployments/README.md").read_text().casefold()
    assert "no terraform" in docs
    assert "secret values" in docs
    assert "must not be committed" in docs
    assert "deployment recipes" in readme
    assert "private review" in readme
    assert "fake" in examples and "deploy" in examples
