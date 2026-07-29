import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.services.operator_diagnostics import collect_configuration_summary
from app.services.private_workspace import write_private_workspace
from app.services.storage import (
    StorageProviderBlockedError,
    StorageProviderConfigError,
    build_storage_provider,
    build_storage_provider_readiness,
    mask_storage_ref,
    validate_storage_key,
)

ROOT = Path(__file__).resolve().parents[1]


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def local(tmp_path: Path, **values):
    root = tmp_path / "private-storage"
    settings = configured(
        local_storage_root=root,
        local_storage_allow_absolute_root=True,
        **values,
    )
    return build_storage_provider("local", settings), root


def test_local_write_read_exists_list_delete_is_sanitized(tmp_path: Path) -> None:
    provider, root = local(tmp_path)
    value = b"private-value-must-not-be-reported"
    written = provider.write("attachments/example.txt", value)
    assert provider.exists("attachments/example.txt")
    assert provider.read("attachments/example.txt") == value
    listing = provider.list()
    assert listing.items and str(root) not in listing.model_dump_json()
    assert value.decode() not in listing.model_dump_json()
    assert written.masked_ref != "attachments/example.txt"
    assert provider.delete("attachments/example.txt").deleted
    assert not provider.exists("attachments/example.txt")


@pytest.mark.parametrize(
    "key",
    [
        "../escape.txt",
        "/absolute.txt",
        "report.pdf",
        "database.db",
        "https://files.invalid/a.txt?token=fake",
        "postgresql://operator@database.invalid/a.txt",
        "support-bundle/private.txt",
    ],
)
def test_unsafe_keys_fail_closed_without_echo(tmp_path: Path, key: str) -> None:
    provider, _ = local(tmp_path)
    with pytest.raises(StorageProviderBlockedError) as error:
        provider.write(key, b"safe")
    assert key not in str(error.value)


def test_local_blocks_symlink_escape(tmp_path: Path) -> None:
    provider, root = local(tmp_path)
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private outside value")
    (root / "linked.txt").symlink_to(outside)
    with pytest.raises(StorageProviderBlockedError):
        provider.read("linked.txt")


def test_local_blocks_oversize_binary_extension_and_overwrite(tmp_path: Path) -> None:
    provider, _ = local(tmp_path, local_storage_max_bytes=8)
    with pytest.raises(StorageProviderBlockedError):
        provider.write("large.txt", b"123456789")
    with pytest.raises(StorageProviderBlockedError):
        provider.write("binary.txt", b"x\x00y")
    with pytest.raises(StorageProviderBlockedError):
        provider.write("image.png", b"text")
    provider.write("same.txt", b"one")
    with pytest.raises(StorageProviderBlockedError):
        provider.write("same.txt", b"two")


def test_absolute_and_unmarked_roots_are_blocked(tmp_path: Path) -> None:
    with pytest.raises(StorageProviderConfigError):
        build_storage_provider(
            "local", configured(local_storage_root=tmp_path / "private-storage")
        )
    with pytest.raises(StorageProviderConfigError):
        build_storage_provider(
            "local",
            configured(
                local_storage_root=tmp_path / "ordinary",
                local_storage_allow_absolute_root=True,
            ),
        )


def test_refs_normalize_mask_and_value_guard() -> None:
    assert validate_storage_key("folder//file.txt") == "folder/file.txt"
    with pytest.raises(StorageProviderBlockedError):
        validate_storage_key("folder/../file.txt")
    assert mask_storage_ref("folder/file.txt") != "folder/file.txt"


@pytest.mark.parametrize("kind", ["s3", "azure_blob", "gcs"])
def test_cloud_adapters_are_disabled_no_call_and_fail_closed(kind: str) -> None:
    settings = configured(storage_provider=kind)
    provider = build_storage_provider(kind, settings)
    health = provider.health()
    assert not health.available
    assert health.external_calls is False
    assert health.operation_not_attempted is True
    with pytest.raises(StorageProviderBlockedError):
        provider.read("safe.txt")


def test_readiness_diagnostics_and_workspace_never_expose_values(
    tmp_path: Path,
) -> None:
    marker = "private-storage-value-d2"
    settings = configured(admin_token=marker)
    readiness = build_storage_provider_readiness(settings)
    summary = collect_configuration_summary(settings)
    serialized = readiness.model_dump_json() + json.dumps(summary.model_dump(mode="json"))
    assert marker not in serialized
    assert readiness.external_calls is False
    root = tmp_path / "private-workspace"
    result = write_private_workspace("sandbox_and_pilot", root)
    expected = {
        "storage/README.private.md",
        "storage/storage-map.private.json",
        "storage/local-storage-root.private.md",
        "storage/object-refs.private.json",
    }
    assert expected.issubset(result.files)


@pytest.mark.parametrize(
    "script",
    [
        "print_storage_provider_template.py",
        "check_storage_refs.py",
        "check_attachment_storage.py",
        "test_local_storage_provider.py",
    ],
)
def test_storage_clis_are_offline_and_sanitized(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "private-storage-value-d2" not in output
    assert "external_calls" in output or "not displayed" in output


def test_docs_make_gitignore_and_no_public_storage_route() -> None:
    assert (ROOT / "docs" / "storage-providers.md").is_file()
    makefile = (ROOT / "Makefile").read_text()
    assert "storage-provider-check:" in makefile
    assert "local-storage-provider-check:" in makefile
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert "local-storage-provider-check" not in quality
    ignored = (ROOT / ".gitignore").read_text()
    for marker in ("private-storage/", ".local-storage/", "object-storage/"):
        assert marker in ignored
    routes = "\n".join(
        path.read_text() for path in (ROOT / "app" / "routes").glob("*.py")
    )
    assert "/storage/" not in routes
