import io
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas.storage import CloudStorageProviderKind, CloudStorageProviderStatus
from app.services.storage import (
    CLOUD_STORAGE_CONFIRMATION_PHRASE,
    AzureBlobStorageProvider,
    GcsStorageProvider,
    S3StorageProvider,
    StorageProviderBlockedError,
    StorageProviderOperationError,
    build_cloud_storage_provider_health,
    validate_cloud_storage_ref,
    validate_storage_key,
)

ROOT = Path(__file__).resolve().parents[1]


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("kind", "enabled_field"),
    [
        (CloudStorageProviderKind.S3, "s3_storage_enabled"),
        (CloudStorageProviderKind.AZURE_BLOB, "azure_blob_storage_enabled"),
        (CloudStorageProviderKind.GCS, "gcs_storage_enabled"),
    ],
)
def test_cloud_storage_providers_disabled_by_default(kind, enabled_field):
    settings = configured()
    assert getattr(settings, enabled_field) is False
    health = build_cloud_storage_provider_health(kind, settings)
    assert health.status is CloudStorageProviderStatus.DISABLED
    assert health.operations_allowed is False
    assert health.health_network_check_attempted is False
    assert health.external_calls is False


def test_cloud_storage_network_and_destructive_operations_default_off():
    settings = configured()
    assert settings.storage_provider_cloud_network_enabled is False
    assert settings.storage_provider_cloud_confirmation == ""
    assert settings.storage_provider_cloud_allow_list is False
    assert settings.storage_provider_cloud_allow_delete is False
    assert settings.storage_provider_cloud_allow_overwrite is False
    assert settings.storage_provider_cloud_allow_presigned_urls is False


class S3Client:
    def __init__(self, value=b"fake-s3-placeholder-content", error=None):
        self.value = value
        self.error = error
        self.calls = []

    def _call(self, name, kwargs):
        self.calls.append(name)
        if self.error:
            raise self.error
        return kwargs

    def put_object(self, **kwargs):
        self._call("put", kwargs)

    def get_object(self, **kwargs):
        self._call("get", kwargs)
        return {"Body": io.BytesIO(self.value)}

    def head_object(self, **kwargs):
        self._call("head", kwargs)
        return {"ContentLength": len(self.value)}

    def delete_object(self, **kwargs):
        self._call("delete", kwargs)

    def list_objects_v2(self, **kwargs):
        self._call("list", kwargs)
        return {"Contents": []}


def s3_provider(monkeypatch, client, **overrides):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    monkeypatch.setenv("S3_BUCKET_NAME", "example-bucket-placeholder")
    return S3StorageProvider(
        configured(
            storage_provider="s3",
            storage_provider_allow_cloud=True,
            storage_provider_cloud_network_enabled=True,
            storage_provider_cloud_confirmation=CLOUD_STORAGE_CONFIRMATION_PHRASE,
            s3_storage_enabled=True,
            **overrides,
        ),
        client=client,
    )


def test_missing_confirmation_blocks_operation_without_client_call(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    monkeypatch.setenv("S3_BUCKET_NAME", "example-bucket-placeholder")
    client = S3Client()
    provider = S3StorageProvider(
        configured(
            storage_provider="s3",
            storage_provider_allow_cloud=True,
            storage_provider_cloud_network_enabled=True,
            s3_storage_enabled=True,
        ),
        client=client,
    )
    with pytest.raises(StorageProviderBlockedError):
        provider.read("S3_OBJECT_KEY_PLACEHOLDER.txt")
    assert client.calls == []


def test_unselected_provider_cannot_contact_client(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "example-region-placeholder")
    monkeypatch.setenv("S3_BUCKET_NAME", "example-bucket-placeholder")
    client = S3Client()
    provider = S3StorageProvider(
        configured(
            storage_provider="local",
            storage_provider_allow_cloud=True,
            storage_provider_cloud_network_enabled=True,
            storage_provider_cloud_confirmation=CLOUD_STORAGE_CONFIRMATION_PHRASE,
            s3_storage_enabled=True,
        ),
        client=client,
    )
    with pytest.raises(StorageProviderBlockedError):
        provider.exists("S3_OBJECT_KEY_PLACEHOLDER.txt")
    assert client.calls == []


def test_missing_dependency_and_config_are_cleanly_reported(monkeypatch):
    monkeypatch.setattr(S3StorageProvider, "_dependency_present", lambda self: False)
    missing_dependency = build_cloud_storage_provider_health(
        CloudStorageProviderKind.S3,
        configured(
            storage_provider="s3",
            storage_provider_allow_cloud=True,
            s3_storage_enabled=True,
        ),
    )
    assert missing_dependency.status is CloudStorageProviderStatus.DEPENDENCY_MISSING
    assert "traceback" not in missing_dependency.model_dump_json().casefold()
    monkeypatch.setattr(S3StorageProvider, "_dependency_present", lambda self: True)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    missing_config = build_cloud_storage_provider_health(
        CloudStorageProviderKind.S3,
        configured(
            storage_provider="s3",
            storage_provider_allow_cloud=True,
            s3_storage_enabled=True,
        ),
    )
    assert missing_config.status is CloudStorageProviderStatus.NEEDS_CONFIGURATION


def test_s3_mocked_write_read_head_are_internal_and_sanitized(monkeypatch):
    value = b"must-not-appear-s3-object-content"
    client = S3Client(value)
    provider = s3_provider(monkeypatch, client)
    written = provider.write("S3_OBJECT_KEY_PLACEHOLDER.txt", value)
    assert provider.read("S3_OBJECT_KEY_PLACEHOLDER.txt") == value
    assert provider.exists("S3_OBJECT_KEY_PLACEHOLDER.txt")
    rendered = written.model_dump_json() + provider.health().model_dump_json()
    assert value.decode() not in rendered
    assert "S3_OBJECT_KEY_PLACEHOLDER.txt" not in rendered
    assert client.calls == ["put", "get", "head"]


def test_s3_write_uses_no_overwrite_precondition(monkeypatch):
    client = S3Client()
    provider = s3_provider(monkeypatch, client)
    provider.write("S3_OBJECT_KEY_PLACEHOLDER.txt", b"fake-placeholder-content")
    assert client.calls == ["put"]


def test_s3_delete_list_and_presigned_urls_remain_blocked(monkeypatch):
    client = S3Client()
    provider = s3_provider(monkeypatch, client)
    with pytest.raises(StorageProviderBlockedError):
        provider.delete("S3_OBJECT_KEY_PLACEHOLDER.txt")
    with pytest.raises(StorageProviderBlockedError):
        provider.list()
    assert not hasattr(provider, "generate_presigned_url")
    assert client.calls == []


def test_s3_delete_and_list_require_explicit_independent_gates(monkeypatch):
    client = S3Client()
    provider = s3_provider(
        monkeypatch,
        client,
        storage_provider_cloud_allow_delete=True,
        storage_provider_cloud_allow_list=True,
    )
    assert provider.delete("S3_OBJECT_KEY_PLACEHOLDER.txt").deleted is True
    assert provider.list().items == []
    assert client.calls == ["delete", "list"]


def test_s3_error_is_sanitized(monkeypatch):
    marker = "must-not-appear-s3-provider-detail"
    provider = s3_provider(monkeypatch, S3Client(error=RuntimeError(marker)))
    with pytest.raises(StorageProviderOperationError) as error:
        provider.read("S3_OBJECT_KEY_PLACEHOLDER.txt")
    assert marker not in str(error.value)


class AzureBlob:
    def __init__(self, owner, name):
        self.owner = owner
        self.name = name

    def upload_blob(self, data, overwrite):
        self.owner._call("upload")
        self.owner.value = data
        self.owner.overwrite = overwrite

    def download_blob(self):
        self.owner._call("download")
        return SimpleNamespace(readall=lambda: self.owner.value)

    def get_blob_properties(self):
        self.owner._call("properties")
        return SimpleNamespace(size=len(self.owner.value))

    def delete_blob(self):
        self.owner._call("delete")


class AzureContainer:
    def __init__(self, value=b"fake-azure-placeholder-content", error=None):
        self.value = value
        self.error = error
        self.calls = []
        self.overwrite = None

    def _call(self, name):
        self.calls.append(name)
        if self.error:
            raise self.error

    def get_blob_client(self, name):
        return AzureBlob(self, name)

    def list_blobs(self, **kwargs):
        self._call("list")
        return []


def azure_provider(monkeypatch, client, **overrides):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "example-account-placeholder")
    monkeypatch.setenv("AZURE_BLOB_CONTAINER_NAME", "example-container-placeholder")
    return AzureBlobStorageProvider(
        configured(
            storage_provider="azure_blob",
            storage_provider_allow_cloud=True,
            storage_provider_cloud_network_enabled=True,
            storage_provider_cloud_confirmation=CLOUD_STORAGE_CONFIRMATION_PHRASE,
            azure_blob_storage_enabled=True,
            **overrides,
        ),
        client=client,
    )


def test_azure_mocked_operations_are_internal_and_health_offline(monkeypatch):
    value = b"must-not-appear-azure-object-content"
    client = AzureContainer()
    provider = azure_provider(monkeypatch, client)
    provider.health()
    assert client.calls == []
    result = provider.write("AZURE_BLOB_NAME_PLACEHOLDER.txt", value)
    assert client.overwrite is False
    assert provider.read("AZURE_BLOB_NAME_PLACEHOLDER.txt") == value
    assert provider.exists("AZURE_BLOB_NAME_PLACEHOLDER.txt")
    assert value.decode() not in result.model_dump_json()
    with pytest.raises(StorageProviderBlockedError):
        provider.delete("AZURE_BLOB_NAME_PLACEHOLDER.txt")


@pytest.mark.parametrize("message", ["fake-auth", "fake-not-found", "fake-permission"])
def test_azure_errors_are_sanitized(monkeypatch, message):
    provider = azure_provider(monkeypatch, AzureContainer(error=RuntimeError(message)))
    with pytest.raises(StorageProviderOperationError) as error:
        provider.read("AZURE_BLOB_NAME_PLACEHOLDER.txt")
    assert message not in str(error.value)


class GcsBlob:
    def __init__(self, owner, name):
        self.owner = owner
        self.name = name

    def upload_from_string(self, data, **kwargs):
        self.owner._call("upload")
        self.owner.value = data
        self.owner.upload_kwargs = kwargs

    def download_as_bytes(self):
        self.owner._call("download")
        return self.owner.value

    def exists(self):
        self.owner._call("exists")
        return True

    def delete(self):
        self.owner._call("delete")


class GcsBucket:
    def __init__(self, owner):
        self.owner = owner

    def blob(self, name):
        return GcsBlob(self.owner, name)


class GcsClient:
    def __init__(self, value=b"fake-gcs-placeholder-content", error=None):
        self.value = value
        self.error = error
        self.calls = []
        self.upload_kwargs = None

    def _call(self, name):
        self.calls.append(name)
        if self.error:
            raise self.error

    def bucket(self, name):
        return GcsBucket(self)

    def list_blobs(self, bucket, prefix):
        self._call("list")
        return []


def gcs_provider(monkeypatch, client, **overrides):
    monkeypatch.setenv("GCP_PROJECT_ID", "example-project-placeholder")
    monkeypatch.setenv("GCS_BUCKET_NAME", "example-bucket-placeholder")
    return GcsStorageProvider(
        configured(
            storage_provider="gcs",
            storage_provider_allow_cloud=True,
            storage_provider_cloud_network_enabled=True,
            storage_provider_cloud_confirmation=CLOUD_STORAGE_CONFIRMATION_PHRASE,
            gcs_storage_enabled=True,
            **overrides,
        ),
        client=client,
    )


def test_gcs_mocked_operations_are_internal_and_no_overwrite(monkeypatch):
    value = b"must-not-appear-gcs-object-content"
    client = GcsClient()
    provider = gcs_provider(monkeypatch, client)
    result = provider.write("GCS_OBJECT_KEY_PLACEHOLDER.txt", value)
    assert client.upload_kwargs == {"if_generation_match": 0}
    assert provider.read("GCS_OBJECT_KEY_PLACEHOLDER.txt") == value
    assert provider.exists("GCS_OBJECT_KEY_PLACEHOLDER.txt")
    assert value.decode() not in result.model_dump_json()
    with pytest.raises(StorageProviderBlockedError):
        provider.delete("GCS_OBJECT_KEY_PLACEHOLDER.txt")


@pytest.mark.parametrize("message", ["fake-auth", "fake-not-found", "fake-permission"])
def test_gcs_errors_are_sanitized(monkeypatch, message):
    provider = gcs_provider(monkeypatch, GcsClient(error=RuntimeError(message)))
    with pytest.raises(StorageProviderOperationError) as error:
        provider.read("GCS_OBJECT_KEY_PLACEHOLDER.txt")
    assert message not in str(error.value)


@pytest.mark.parametrize(
    ("provider", "unsafe_ref"),
    [
        ("s3", "s3://example-placeholder/fake-placeholder"),
        ("s3", "arn:aws:s3:::example-placeholder"),
        ("azure_blob", "https://example-placeholder.blob.core.windows.net/fake"),
        ("gcs", "gs://example-placeholder/fake-placeholder"),
        ("gcs", "projects/example-placeholder/buckets/fake-placeholder"),
        ("s3", '{"private_key":"fake-placeholder"}'),
        ("s3", "-----BEGIN PRIVATE KEY----- fake-placeholder"),
        ("s3", "Authorization: Bearer fake-placeholder"),
        ("s3", "postgresql://example:placeholder@database.invalid/example"),
        ("s3", "https://example.invalid/object?signature=fake-placeholder"),
        ("s3", "/home/example/.aws/credentials"),
        ("s3", "123456789012"),
        ("azure_blob", "00000000-0000-0000-0000-000000000000"),
    ],
)
def test_cloud_storage_ref_validation_blocks_unsafe(provider, unsafe_ref):
    with pytest.raises(StorageProviderBlockedError) as error:
        validate_cloud_storage_ref(unsafe_ref, provider)
    assert unsafe_ref not in str(error.value)


@pytest.mark.parametrize(
    ("provider", "ref"),
    [
        ("s3", "S3_BUCKET_REF_PLACEHOLDER"),
        ("azure_blob", "AZURE_BLOB_CONTAINER_REF_PLACEHOLDER"),
        ("gcs", "GCS_BUCKET_REF_PLACEHOLDER"),
    ],
)
def test_placeholder_storage_refs_allowed(provider, ref):
    assert validate_cloud_storage_ref(ref, provider) == ref


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "support-bundle/private.txt",
        "live-attachment.pdf",
        "https://example.invalid/object?token=fake-placeholder",
    ],
)
def test_storage_keys_block_private_or_attachment_patterns(unsafe_key):
    with pytest.raises(StorageProviderBlockedError):
        validate_storage_key(unsafe_key)


@pytest.mark.parametrize(
    "script",
    [
        "check_cloud_storage_provider.py",
        "print_cloud_storage_provider_template.py",
        "explain_cloud_storage_operations.py",
    ],
)
def test_cloud_storage_cli_is_offline_and_sanitized(script):
    marker = "must-not-appear-cloud-storage-content"
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
    assert "s3://" not in result.stdout.casefold()
    assert "gs://" not in result.stdout.casefold()
    assert ".blob.core.windows.net" not in result.stdout.casefold()


def test_make_docs_and_examples_cover_g2():
    makefile = (ROOT / "Makefile").read_text()
    quality = next(line for line in makefile.splitlines() if line.startswith("quality:"))
    for target in (
        "cloud-storage-template",
        "cloud-storage-check",
        "cloud-storage-explain",
    ):
        assert f"{target}:" in makefile
        assert target in quality
    docs = (ROOT / "docs/cloud-storage-providers.md").read_text().casefold()
    assert "local provider first" in docs
    assert "optional" in docs and "disabled by default" in docs
    assert "never contact cloud" in docs
    assert "no presigned url" in docs
    for path in (ROOT / "examples/cloud-storage-providers").glob("*.json"):
        contents = path.read_text()
        assert "PLACEHOLDER" in contents
        assert '"object_contents_included": false' in contents


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "s3://private-bucket-name/records/item.txt",
        "arn:aws:s3:::private-bucket-name",
        "https://privateaccount.blob.core.windows.net/privatecontainer/item.txt",
        "gs://private-bucket-name/records/item.txt",
    ],
)
def test_public_safety_audit_rejects_cloud_storage_resource_ids(
    tmp_path, unsafe_text
):
    target = tmp_path / "unsafe-cloud-storage.md"
    target.write_text(unsafe_text)
    result = subprocess.run(
        [sys.executable, "scripts/audit_public_safety.py", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert unsafe_text not in result.stdout


def test_public_safety_audit_rejects_literal_object_content(tmp_path):
    example_dir = tmp_path / "examples/cloud-storage-providers"
    example_dir.mkdir(parents=True)
    target = example_dir / "unsafe.example.json"
    marker = "private-live-object-content"
    target.write_text(f'{{"object_content": "{marker}"}}')
    result = subprocess.run(
        [sys.executable, "scripts/audit_public_safety.py", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert marker not in result.stdout
