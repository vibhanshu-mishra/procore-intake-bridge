import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.security.secret_provider_factory import build_secret_provider
from app.security.secret_refs import SecretRefError, mask_secret_ref, validate_secret_ref
from app.security.secrets import (
    AwsSecretsManagerProvider,
    EnvSecretProvider,
    FileSecretProvider,
    SecretNotFoundError,
    SecretProviderBlockedError,
    SecretProviderConfigError,
    SecretProviderUnavailableError,
)
from app.services.private_workspace import write_private_workspace
from app.services.secrets import (
    assert_secret_value_never_reported,
    build_secret_provider_health,
    build_secret_provider_readiness,
)
from app.services.usage_modes import (
    build_demo_mode_readiness,
    build_pilot_mode_readiness,
    build_sandbox_mode_readiness,
    build_usage_mode_doctor_report,
)

ROOT = Path(__file__).resolve().parents[1]


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_env_provider_resolves_internally_and_never_reports_value(
    monkeypatch,
) -> None:
    ref = "PROCORE_INTAKE_SECRET_EXAMPLE_D1"
    value = "fake-d1-environment-secret-value"
    monkeypatch.setenv(ref, value)
    provider = EnvSecretProvider(configured())
    assert provider.get_secret(ref) == value
    health = provider.health_check([ref])
    serialized = json.dumps(health, default=lambda item: item.__dict__)
    assert value not in serialized
    assert ref not in serialized
    assert health.present_refs_count == 1


def test_env_missing_error_is_sanitized_and_environment_is_not_dumped(
    monkeypatch,
) -> None:
    missing = "PROCORE_INTAKE_SECRET_EXAMPLE_MISSING_D1"
    unrelated = "must-not-appear-unrelated-env-value"
    monkeypatch.delenv(missing, raising=False)
    monkeypatch.setenv("UNRELATED_PRIVATE_VALUE", unrelated)
    with pytest.raises(SecretNotFoundError) as error:
        EnvSecretProvider(configured()).get_secret(missing)
    assert missing not in str(error.value)
    assert unrelated not in str(error.value)


def _file_settings(root: Path, **values) -> Settings:
    return configured(secret_provider="file", file_secret_root=root, **values)


def test_file_provider_resolves_text_and_strips_trailing_newline(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private-secrets"
    target = root / "dmsa/client_secret.secret"
    target.parent.mkdir(parents=True)
    value = "fake-d1-file-secret-value"
    target.write_text(value + "\r\n")
    provider = FileSecretProvider(_file_settings(root))
    assert provider.get_secret("dmsa/client_secret.secret") == value
    health = provider.health_check(["dmsa/client_secret.secret"])
    assert value not in json.dumps(health, default=lambda item: item.__dict__)
    assert str(root) not in json.dumps(health, default=lambda item: item.__dict__)


@pytest.mark.parametrize(
    "ref",
    [
        "../outside.secret",
        "/tmp/private-secrets/outside.secret",
        "report.pdf",
        "archive.zip",
        "image.png",
        "database.db",
    ],
)
def test_file_provider_blocks_unsafe_refs(tmp_path: Path, ref: str) -> None:
    with pytest.raises(SecretProviderBlockedError):
        FileSecretProvider(_file_settings(tmp_path / "private-secrets")).get_secret(
            ref
        )


def test_file_provider_blocks_symlink_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "private-secrets"
    root.mkdir()
    outside = tmp_path / "outside.secret"
    outside.write_text("fake-outside-secret-value")
    (root / "linked.secret").symlink_to(outside)
    with pytest.raises(SecretProviderBlockedError):
        FileSecretProvider(_file_settings(root)).get_secret("linked.secret")


def test_file_provider_blocks_oversize_binary_and_unsafe_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private-secrets"
    root.mkdir()
    (root / "large.secret").write_text("x" * 20)
    with pytest.raises(SecretProviderBlockedError):
        FileSecretProvider(
            _file_settings(root, file_secret_max_bytes=8)
        ).get_secret("large.secret")
    (root / "binary.secret").write_bytes(b"fake\x00binary")
    with pytest.raises(SecretProviderBlockedError):
        FileSecretProvider(_file_settings(root)).get_secret("binary.secret")
    with pytest.raises(SecretProviderConfigError):
        FileSecretProvider(_file_settings(tmp_path / "ordinary")).get_secret(
            "missing.secret"
        )


def test_file_errors_do_not_include_contents(tmp_path: Path) -> None:
    root = tmp_path / "private-secrets"
    root.mkdir()
    value = "must-not-appear-file-secret"
    (root / "binary.secret").write_bytes(value.encode() + b"\x00")
    with pytest.raises(SecretProviderBlockedError) as error:
        FileSecretProvider(_file_settings(root)).get_secret("binary.secret")
    assert value not in str(error.value)
    assert str(root) not in str(error.value)


@pytest.mark.parametrize(
    "ref",
    [
        "Authorization: Bearer fake-private-token",
        "postgresql://operator:placeholder@database.invalid/db",
        "https://files.invalid/x?signature=fake-private-signature",
        "SECRET_VALUE=fake-private-value",
    ],
)
def test_inline_secret_like_refs_are_blocked_without_echo(ref: str) -> None:
    with pytest.raises(SecretRefError) as error:
        validate_secret_ref(ref, configured())
    assert ref not in str(error.value)


def test_placeholder_refs_normalize_and_mask() -> None:
    ref = "ENV_REF_PLACEHOLDER_DMSA_CLIENT_SECRET"
    validated = validate_secret_ref(ref, configured())
    masked = mask_secret_ref(validated.name, configured())
    assert masked != ref
    assert "DMSA_CLIENT" not in masked


def test_value_reporting_guard_always_blocks() -> None:
    with pytest.raises(SecretProviderBlockedError):
        assert_secret_value_never_reported("fake-private-value")


def test_cloud_providers_are_disabled_and_no_call_health_is_fail_closed() -> None:
    settings = configured(
        secret_provider="aws_secrets_manager",
        secret_provider_allow_cloud=False,
        aws_secrets_enabled=False,
    )
    provider = build_secret_provider(settings)
    assert isinstance(provider, AwsSecretsManagerProvider)
    health = provider.health_check(["PROCORE_INTAKE_SECRET_EXAMPLE_CLOUD"])
    assert health.status == "unavailable"
    assert "no external call" in health.message.casefold()
    with pytest.raises(SecretProviderBlockedError):
        provider.get_secret("PROCORE_INTAKE_SECRET_EXAMPLE_CLOUD")


def test_cloud_enabled_without_dependency_or_private_config_fails_closed() -> None:
    provider = AwsSecretsManagerProvider(
        configured(
            secret_provider="aws_secrets_manager",
            secret_provider_allow_cloud=True,
            aws_secrets_enabled=True,
        )
    )
    with pytest.raises(
        (SecretProviderUnavailableError, SecretProviderConfigError)
    ):
        provider.get_secret("PROCORE_INTAKE_SECRET_EXAMPLE_CLOUD")


def test_health_and_readiness_are_sanitized(monkeypatch) -> None:
    ref = "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_D1"
    value = "fake-admin-d1-secret-value"
    monkeypatch.setenv(ref, value)
    settings = configured(
        admin_require_token=True,
        admin_token_secret_name=ref,
    )
    health = build_secret_provider_health(settings)
    readiness = build_secret_provider_readiness(settings)
    serialized = health.model_dump_json() + readiness.model_dump_json()
    assert value not in serialized
    assert ref not in serialized
    assert readiness.ready is True


def test_mode_doctor_secret_posture_is_safe() -> None:
    assert build_demo_mode_readiness(configured()).secrets_required is False
    sandbox = build_sandbox_mode_readiness(configured())
    pilot = build_pilot_mode_readiness(configured())
    assert "secret_provider" in {item.requirement for item in sandbox.requirements}
    assert "secret_provider_posture" in {
        item.requirement for item in pilot.requirements
    }
    assert (
        build_pilot_mode_readiness(
            configured(secret_provider="external_placeholder")
        ).status.value
        == "needs_configuration"
    )
    marker = "must-not-appear-doctor-secret"
    report = build_usage_mode_doctor_report(
        configured(admin_token=marker)
    ).model_dump_json()
    assert marker not in report


def test_private_workspace_contains_refs_but_no_values(tmp_path: Path) -> None:
    root = tmp_path / "private-workspace"
    result = write_private_workspace("sandbox_and_pilot", root)
    assert "environment/secrets/README.private.md" in result.files
    contents = "\n".join(
        path.read_text() for path in root.rglob("*") if path.is_file()
    )
    assert "ENV_REF_PLACEHOLDER_PROCORE_CLIENT_ID" in contents
    assert "dmsa/client_secret.secret" in contents
    assert "secret_values_included" in contents
    assert '"secret_values_included": false' in contents


@pytest.mark.parametrize(
    "script",
    [
        "check_secret_provider.py",
        "print_secret_provider_template.py",
        "check_secret_refs.py",
        "test_file_secret_provider.py",
    ],
)
def test_secret_cli_scripts_are_safe(script: str) -> None:
    marker = "must-not-appear-cli-secret"
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "UNRELATED_PRIVATE_VALUE": marker},
    )
    assert result.returncode == 0, result.stderr
    assert marker not in result.stdout
    assert str(ROOT) not in result.stdout


def test_docs_makefile_and_ignore_rules_cover_d1() -> None:
    readme = (ROOT / "README.md").read_text().casefold()
    docs = (ROOT / "docs/secret-providers.md").read_text().casefold()
    makefile = (ROOT / "Makefile").read_text()
    ignored = (ROOT / ".gitignore").read_text()
    assert "secret provider" in readme
    assert "demo mode needs no secrets" in docs
    assert "env provider" in docs and "file provider" in docs
    assert "optional" in docs and "fail closed" in docs
    for target in (
        "secret-provider-template",
        "secret-provider-check",
        "secret-refs-check",
        "file-secret-provider-check",
    ):
        assert f"{target}:" in makefile
    assert "private-secrets/" in ignored
