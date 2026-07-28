import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.models.attachment_objects import AttachmentObject
from app.services.attachment_storage import (
    AttachmentStorageError,
    set_attachment_download_status,
)
from app.services.attachment_storage_factory import (
    build_attachment_storage_provider,
    summarize_attachment_storage_config,
)
from app.services.attachment_storage_inventory import (
    check_manifest_storage_consistency,
)
from app.services.attachment_storage_keys import (
    AttachmentStorageKeyError,
    build_safe_storage_key,
    mask_storage_key,
    normalize_storage_key,
    validate_storage_key,
)
from app.services.attachment_storage_provider import (
    AttachmentStorageBlockedError,
    AttachmentStorageMisconfiguredError,
    AttachmentStorageUnavailableError,
    ExternalPlaceholderAttachmentStorageProvider,
)
from app.services.deployment_readiness import check_attachment_storage_safety


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/private/example.bin",
        "../secret.bin",
        "safe/../../secret.bin",
        "https://example.invalid/object",
        "safe/\x00bad.bin",
    ],
)
def test_storage_keys_reject_unsafe_values(key):
    with pytest.raises(AttachmentStorageKeyError):
        validate_storage_key(key)


def test_storage_keys_normalize_mask_and_build_deterministically():
    assert normalize_storage_key(r"safe\\folder//file.pdf") == "safe/folder/file.pdf"
    first = build_safe_storage_key(1, "../../project", "rfi", "/item", "../../file.pdf")
    second = build_safe_storage_key(1, "../../project", "rfi", "/item", "../../file.pdf")
    assert first == second
    assert first == "connection-1/project-project/rfi-item/file.pdf"
    assert mask_storage_key(first).startswith("object-")
    assert "connection-1" not in mask_storage_key(first)


def test_local_provider_stays_under_root_and_returns_safe_results(tmp_path):
    settings = Settings(_env_file=None, attachment_storage_root=tmp_path)
    provider = build_attachment_storage_provider(settings)
    result = provider.write_bytes("safe/object.bin", b"fixture")
    assert result.storage_key == "safe/object.bin"
    assert result.size_bytes == 7
    assert (tmp_path / "safe/object.bin").read_bytes() == b"fixture"
    assert str(tmp_path) not in json.dumps(provider.describe_object("safe/object.bin"))
    with pytest.raises((AttachmentStorageBlockedError, AttachmentStorageKeyError)):
        provider.write_bytes("../escape.bin", b"blocked")


def test_local_provider_overwrite_fails_closed(tmp_path):
    settings = Settings(_env_file=None, attachment_storage_root=tmp_path)
    provider = build_attachment_storage_provider(settings)
    provider.write_bytes("safe/object.bin", b"first")
    with pytest.raises(AttachmentStorageBlockedError):
        provider.write_bytes("safe/object.bin", b"second", overwrite=True)


def test_test_provider_is_in_memory():
    settings = Settings(_env_file=None, attachment_storage_provider="test")
    provider = build_attachment_storage_provider(settings)
    provider.write_bytes("fixture.bin", b"fixture")
    assert provider.read_bytes("fixture.bin").data == b"fixture"
    assert provider.exists("fixture.bin")


def test_disabled_and_external_placeholder_fail_closed():
    disabled = build_attachment_storage_provider(
        Settings(_env_file=None, attachment_storage_provider="disabled")
    )
    with pytest.raises(AttachmentStorageBlockedError):
        disabled.write_bytes("fixture.bin", b"fixture")
    external = ExternalPlaceholderAttachmentStorageProvider()
    with pytest.raises(AttachmentStorageUnavailableError):
        external.read_bytes("fixture.bin")
    assert external.health_check().implemented is False


def test_unknown_provider_fails_closed():
    settings = Settings(_env_file=None)
    settings.attachment_storage_provider = "unknown"
    with pytest.raises(AttachmentStorageMisconfiguredError):
        build_attachment_storage_provider(settings)


def test_config_summary_exposes_no_root_or_external_values(tmp_path):
    settings = Settings(
        _env_file=None,
        attachment_storage_root=tmp_path / "private-root",
        attachment_storage_provider="external_placeholder",
        attachment_storage_external_bucket_ref="SECRET_BUCKET_REFERENCE",
        attachment_storage_external_endpoint_ref="SECRET_ENDPOINT_REFERENCE",
    )
    rendered = json.dumps(summarize_attachment_storage_config(settings))
    assert str(tmp_path) not in rendered
    assert "SECRET_BUCKET_REFERENCE" not in rendered
    assert "SECRET_ENDPOINT_REFERENCE" not in rendered
    assert '"external_calls": false' in rendered


def test_external_placeholder_blocks_production_readiness():
    findings = check_attachment_storage_safety(
        Settings(
            _env_file=None,
            environment="production",
            attachment_storage_provider="external_placeholder",
        )
    )
    assert any("production" in finding.blocks for finding in findings)


def test_non_fixture_downloads_block_production_readiness():
    findings = check_attachment_storage_safety(
        Settings(
            _env_file=None,
            environment="production",
            attachment_fixture_downloads_only=False,
        )
    )
    assert any(
        "Non-fixture" in finding.message and "production" in finding.blocks
        for finding in findings
    )


def test_empty_manifest_consistency_passes(db_session, tmp_path):
    settings = Settings(_env_file=None, attachment_storage_root=tmp_path)
    result = check_manifest_storage_consistency(
        db_session, build_attachment_storage_provider(settings), settings=settings
    )
    assert result["consistent"] is True
    assert result["summary"]["total"] == 0


def test_manifest_consistency_detects_missing_downloaded_object(
    db_session, tmp_path
):
    row = AttachmentObject(
        original_filename="fixture.bin",
        safe_filename="fixture.bin",
        storage_backend="local",
        storage_key="safe/fixture.bin",
        storage_path="safe/fixture.bin",
        download_status="downloaded",
    )
    db_session.add(row)
    db_session.commit()
    settings = Settings(_env_file=None, attachment_storage_root=tmp_path)
    result = check_manifest_storage_consistency(
        db_session, build_attachment_storage_provider(settings), settings=settings
    )
    rendered = json.dumps(result)
    assert result["consistent"] is False
    assert str(tmp_path) not in rendered
    assert "safe/fixture.bin" not in rendered


def test_manifest_status_helper_rejects_unknown_and_sanitizes_failure():
    row = AttachmentObject(
        original_filename="fixture.bin",
        safe_filename="fixture.bin",
        storage_backend="local",
        storage_key="safe/fixture.bin",
        storage_path="safe/fixture.bin",
        download_status="planned",
    )
    with pytest.raises(AttachmentStorageError):
        set_attachment_download_status(row, "unexpected")
    set_attachment_download_status(
        row,
        "failed",
        failure_code="../../Private Failure",
        failure_message="/private/path secret-value",
    )
    assert row.failure_code == "Private_Failure"
    assert "private/path" not in row.failure_message
    assert "secret-value" not in row.failure_message


def test_deployment_storage_route_is_sanitized(client):
    response = client.get("/deployment/storage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["external_calls"] is False
    assert payload["paths_exposed"] is False
    assert "storage/attachments" not in response.text


@pytest.mark.parametrize(
    "script",
    [
        "scripts/check_attachment_storage.py",
        "scripts/check_attachment_manifest_consistency.py",
    ],
)
def test_storage_cli_runs_safely(script, tmp_path):
    result = subprocess.run(
        [sys.executable, script],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": "",
            "PROCORE_INTAKE_DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
            "PROCORE_INTAKE_ATTACHMENT_STORAGE_ROOT": str(tmp_path / "storage"),
        },
    )
    assert result.returncode == 0
    assert str(tmp_path) not in result.stdout
    assert "external_calls" in result.stdout


def test_storage_cli_strict_rejects_unavailable_provider(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/check_attachment_storage.py", "--strict"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": "",
            "PROCORE_INTAKE_ATTACHMENT_STORAGE_PROVIDER": "external_placeholder",
            "PROCORE_INTAKE_DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
        },
    )
    assert result.returncode == 1
