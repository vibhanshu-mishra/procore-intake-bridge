import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.deployment_recipes import (
    DeploymentRecipeProfile,
)
from app.services.deployment_recipes import (
    DeploymentRecipeBlockedError,
    build_deployment_recipe_readiness_report,
    validate_deployment_recipe_profile,
    write_deployment_recipe_artifacts,
)
from app.services.private_workspace import write_private_workspace
from app.services.usage_modes import (
    build_demo_mode_readiness,
    build_pilot_mode_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "deployment-recipes"


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load(name: str) -> DeploymentRecipeProfile:
    return DeploymentRecipeProfile.model_validate_json(
        (EXAMPLES / name).read_text()
    )


@pytest.mark.parametrize(
    "name",
    ["example_docker_local_recipe.json", "example_managed_paas_recipe.json"],
)
def test_fake_recipes_validate_and_are_sanitized(name: str) -> None:
    profile = load(name)
    report = build_deployment_recipe_readiness_report(profile, configured())
    assert report.status == "ready"
    assert not report.findings
    assert report.external_calls is False
    assert report.deployment_executed is False


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("environment_label", "customer-domain.com", "real_domain"),
        ("public_base_url_placeholder", "https://customer.invalid", "raw_url"),
        ("notes", ["password=private-value"], "secret"),
        ("notes", ["Authorization: Bearer fake-value"], "secret"),
        ("notes", ["-----BEGIN PRIVATE KEY-----"], "certificate"),
        ("notes", ["vpc-123456abcdef"], "infrastructure_id"),
        ("notes", ["/Users/operator/deploy"], "absolute_path"),
        ("notes", ["backup.pgdump"], "blocked_file"),
        ("notes", ["operator@customer-domain.com"], "real_domain"),
        ("notes", ["312-555-0199"], "phone"),
        ("notes", ["Procore project 1234567"], "real_id"),
    ],
)
def test_unsafe_recipe_values_are_blocked(field: str, value, code: str) -> None:
    data = load("example_docker_local_recipe.json").model_dump(mode="json")
    data[field] = value
    findings = validate_deployment_recipe_profile(
        DeploymentRecipeProfile.model_validate(data), configured()
    )
    assert code in {item.code for item in findings}


def test_webhook_plan_requires_https_and_ingress() -> None:
    data = load("example_managed_paas_recipe.json").model_dump(mode="json")
    data["tls_status"] = "needs_configuration"
    data["public_ingress_status"] = "blocked"
    findings = validate_deployment_recipe_profile(
        DeploymentRecipeProfile.model_validate(data), configured()
    )
    assert {"https", "public_ingress"} <= {item.code for item in findings}


def test_pilot_recipe_requires_runbook_posture() -> None:
    data = load("example_managed_paas_recipe.json").model_dump(mode="json")
    data["operator_runbook_status"] = "blocked"
    findings = validate_deployment_recipe_profile(
        DeploymentRecipeProfile.model_validate(data), configured()
    )
    assert "operator_runbook" in {item.code for item in findings}


def test_artifact_generation_is_contained_and_safe(tmp_path: Path) -> None:
    root = tmp_path / "procore-intake-bridge-deployment-test"
    profile = load("example_docker_local_recipe.json")
    result = write_deployment_recipe_artifacts(profile, root)
    assert result.output_directory == profile.recipe_name
    contents = "\n".join(path.read_text() for path in root.rglob("*") if path.is_file())
    for blocked in (
        "postgresql://", "-----BEGIN", "/Users/", "Authorization:", "customer.com"
    ):
        assert blocked not in contents
    assert result.external_calls is False
    assert result.deployment_executed is False


def test_artifact_generation_rejects_traversal() -> None:
    with pytest.raises(DeploymentRecipeBlockedError):
        write_deployment_recipe_artifacts(
            load("example_docker_local_recipe.json"),
            Path("../deployment-output"),
        )


def test_private_workspace_contains_deployment_placeholders(tmp_path: Path) -> None:
    root = tmp_path / "private-workspace"
    result = write_private_workspace("sandbox_and_pilot", root)
    expected = {
        "deployment/README.private.md",
        "deployment/deployment-recipe.private.json",
        "deployment/https-tls.private.md",
        "deployment/webhook-ingress.private.md",
        "deployment/cutover-checklist.private.md",
        "deployment/backup-runbook.private.md",
        "deployment/rollback-runbook.private.md",
        "deployment/operator-runbook.private.md",
    }
    assert expected.issubset(result.files)
    contents = "\n".join(path.read_text() for path in root.rglob("*") if path.is_file())
    assert "PUBLIC_BASE_URL_PLACEHOLDER" in contents
    assert "-----BEGIN" not in contents
    assert "postgresql://" not in contents


def test_doctor_mode_posture_keeps_demo_optional_and_pilot_planned() -> None:
    demo = build_demo_mode_readiness(configured())
    pilot = build_pilot_mode_readiness(configured())
    assert "deployment" not in {item.requirement for item in demo.requirements}
    assert "deployment_recipe_posture" in {
        item.requirement for item in pilot.requirements
    }


@pytest.mark.parametrize(
    "command",
    [
        ["print_deployment_recipe_template.py", "--target", "docker_local"],
        ["check_deployment_recipe.py",
         "examples/deployment-recipes/example_docker_local_recipe.json"],
        ["check_deployment_recipe.py",
         "examples/deployment-recipes/example_managed_paas_recipe.json"],
        ["check_deployment_safety.py",
         "examples/deployment-recipes/example_docker_local_recipe.json"],
        ["print_https_webhook_checklist.py"],
    ],
)
def test_deployment_clis_are_offline_and_safe(command: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / command[0]), *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "private-value" not in result.stdout
    assert "/Users/" not in result.stdout


def test_make_docs_examples_and_gitignore_contract() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "deployment-template:" in makefile
    assert "deployment-artifact-check:" in makefile
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert "deployment-artifact-check" not in quality
    for name in (
        "docker-compose.pilot.example.yml",
        "env.pilot.example",
        "nginx.webhook-ingress.example.conf",
    ):
        assert (EXAMPLES / name).is_file()
    ignored = (ROOT / ".gitignore").read_text()
    for marker in ("deployment-output/", "*.pem", "*.tfstate"):
        assert marker in ignored
