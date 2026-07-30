import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.hosted_deployment_templates import (
    HostedDeploymentPlatform,
    HostedDeploymentTemplateProfile,
)
from app.services.hosted_deployment_templates import (
    ARTIFACT_FILES,
    HostedDeploymentTemplateBlockedError,
    build_default_hosted_deployment_profile,
    build_hosted_deployment_report,
    validate_hosted_deployment_profile,
    write_hosted_deployment_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/hosted-deployment-templates"
PROFILE_FILES = tuple(sorted(EXAMPLES.glob("*.example.json")))
FORBIDDEN = (
    "https://",
    "postgresql://",
    "authorization: bearer",
    "-----begin",
    "/users/",
    "/private/",
    "arn:aws",
    "/subscriptions/",
    "projects/",
    "customer.com",
)


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def load(name: str = "docker_vps.example.json") -> HostedDeploymentTemplateProfile:
    return HostedDeploymentTemplateProfile.model_validate_json(
        (EXAMPLES / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("platform", list(HostedDeploymentPlatform))
def test_default_platform_templates_are_placeholder_only(platform):
    profile = build_default_hosted_deployment_profile(platform, settings())
    report = build_hosted_deployment_report(profile, settings())
    assert report.placeholder_only is True
    assert report.status == "needs_configuration"
    assert report.external_calls is False
    assert report.deployment_executed is False
    serialized = json.dumps(profile.model_dump(mode="json")).casefold()
    assert "placeholder" in serialized
    assert not any(value in serialized for value in FORBIDDEN)


@pytest.mark.parametrize("path", PROFILE_FILES, ids=lambda path: path.name)
def test_each_example_profile_validates(path: Path):
    profile = HostedDeploymentTemplateProfile.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    assert not validate_hosted_deployment_profile(profile, settings())


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        ("notes", ["customer.com"], "real_domain"),
        ("notes", ["https://must-not-appear.invalid"], "raw_url"),
        ("container_image_placeholder", "private/image:latest", "registry_ref"),
        (
            "notes",
            ["postgresql://must-not-appear:must-not-appear@must-not-appear.invalid/db"],
            "raw_url",
        ),
        ("notes", ["password=must-not-appear"], "secret"),
        ("notes", ["Authorization: Bearer must-not-appear"], "secret"),
        ("notes", ["arn:aws:ecs:region:123456789012:service/value"], "aws_cloud_id"),
        (
            "notes",
            ["/subscriptions/00000000-0000-0000-0000-000000000000"],
            "azure_cloud_id",
        ),
        ("notes", ["projects/private-project"], "gcp_cloud_id"),
        ("notes", ["vpc-abcdef123456"], "infrastructure_id"),
        ("notes", ["-----BEGIN PRIVATE KEY-----"], "certificate"),
        ("notes", ["/Users/operator/private-hosting"], "absolute_path"),
        ("notes", ["approved for production"], "approval_claim"),
        ("notes", ["DEPLOYMENT_TOKEN=must-not-appear"], "env_value"),
        ("notes", ["private-deployment.log"], "blocked_file"),
    ),
)
def test_unsafe_hosted_values_are_blocked(field, value, code):
    data = load().model_dump(mode="json")
    data[field] = value
    findings = validate_hosted_deployment_profile(
        HostedDeploymentTemplateProfile.model_validate(data), settings()
    )
    assert code in {item.code for item in findings}


def test_unsafe_allowance_settings_fail_closed():
    profile = load()
    findings = validate_hosted_deployment_profile(
        profile, settings(hosted_deployment_allow_real_domains=True)
    )
    assert "unsafe_policy" in {item.code for item in findings}


def test_generated_artifacts_are_contained_and_safe(tmp_path: Path):
    output = tmp_path.parent / "procore-intake-bridge-hosted-deployment-pytest"
    result = write_hosted_deployment_artifacts(load(), output)
    assert result.files == ARTIFACT_FILES
    contents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file()
    ).casefold()
    assert "placeholder" in contents
    assert not any(value in contents for value in FORBIDDEN)
    assert result.external_calls is False
    assert result.deployment_executed is False


def test_artifact_generation_blocks_traversal():
    with pytest.raises(HostedDeploymentTemplateBlockedError):
        write_hosted_deployment_artifacts(load(), Path("../hosted-deployment-output"))


@pytest.mark.parametrize(
    "command",
    (
        ["print_hosted_deployment_template.py", "--platform", "docker_vps"],
        [
            "check_hosted_deployment_template.py",
            "examples/hosted-deployment-templates/docker_vps.example.json",
        ],
        ["print_hosted_deployment_matrix.py"],
        [
            "generate_hosted_deployment_artifacts.py",
            "examples/hosted-deployment-templates/docker_vps.example.json",
            "--temporary",
        ],
    ),
)
def test_hosted_cli_commands_are_offline_and_safe(command):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / command[0]), *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = (result.stdout + result.stderr).casefold()
    assert not any(value in output for value in FORBIDDEN)


def test_snippets_are_placeholder_only_and_not_deployable():
    paths = list((EXAMPLES / "snippets").iterdir())
    assert len(paths) == 9
    contents = "\n".join(
        path.read_text(encoding="utf-8") for path in paths
    ).casefold()
    assert "placeholder" in contents
    assert "not ready" in contents or "not a deployable" in contents
    assert not any(value in contents for value in FORBIDDEN)


def test_makefile_and_docs_contract():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "hosted-deployment-template",
        "hosted-deployment-check",
        "hosted-deployment-matrix",
        "hosted-deployment-artifact-check",
    ):
        assert f"{target}:" in makefile
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    assert "hosted-deployment-template" in quality
    assert "hosted-deployment-check" in quality
    assert "hosted-deployment-matrix" in quality
    assert "hosted-deployment-artifact-check" not in quality
    for name in (
        "hosted-deployment-templates.md",
        "docker-vps-hosting.md",
        "managed-paas-hosting.md",
        "container-platform-hosting.md",
        "cloud-platform-hosting.md",
    ):
        assert (ROOT / "docs" / name).is_file()
        assert name in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
