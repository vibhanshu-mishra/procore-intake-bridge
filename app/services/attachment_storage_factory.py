from app.config import Settings
from app.services.attachment_storage_provider import (
    AttachmentStorageMisconfiguredError,
    DisabledAttachmentStorageProvider,
    ExternalPlaceholderAttachmentStorageProvider,
    LocalAttachmentStorageProvider,
    TestAttachmentStorageProvider,
)


def get_attachment_storage_provider_name(settings: Settings) -> str:
    provider = str(settings.attachment_storage_provider).strip()
    legacy = str(settings.attachment_storage_backend).strip()
    if provider == "local" and legacy and legacy != "local":
        provider = legacy
    return provider


def build_attachment_storage_provider(
    settings: Settings, test_storage: dict[str, bytes] | None = None
):
    name = get_attachment_storage_provider_name(settings)
    if name == "local":
        return LocalAttachmentStorageProvider(settings)
    if name == "test":
        return TestAttachmentStorageProvider(settings, test_storage)
    if name == "disabled":
        return DisabledAttachmentStorageProvider()
    if name == "external_placeholder":
        provider = ExternalPlaceholderAttachmentStorageProvider()
        provider.settings = settings
        return provider
    raise AttachmentStorageMisconfiguredError(
        "Unknown attachment storage provider; storage fails closed."
    )


def summarize_attachment_storage_config(settings: Settings) -> dict:
    name = get_attachment_storage_provider_name(settings)
    summary = {
        "provider": name,
        "safe_keys_required": settings.attachment_storage_require_safe_keys,
        "health_check_enabled": settings.attachment_storage_health_check_enabled,
        "fail_closed": settings.attachment_storage_fail_closed,
        "max_object_bytes": settings.attachment_storage_max_object_bytes,
        "allowed_content_types_configured": bool(
            settings.attachment_storage_allowed_content_types.strip()
        ),
        "quarantine_unknown_types": settings.attachment_storage_quarantine_unknown_types,
        "write_metadata_only": settings.attachment_storage_write_metadata_only,
        "fixture_downloads_only": settings.attachment_fixture_downloads_only,
        "external_calls": False,
    }
    if name == "local":
        summary.update(
            {
                "root_configured": bool(str(settings.attachment_storage_root)),
                "root_is_absolute": settings.attachment_storage_root.is_absolute(),
            }
        )
    if name == "external_placeholder":
        summary.update(
            {
                "external_provider_name_configured": bool(
                    settings.attachment_storage_external_provider_name.strip()
                ),
                "external_bucket_reference_configured": bool(
                    settings.attachment_storage_external_bucket_ref.strip()
                ),
                "external_region_configured": bool(
                    settings.attachment_storage_external_region.strip()
                ),
                "external_endpoint_reference_configured": bool(
                    settings.attachment_storage_external_endpoint_ref.strip()
                ),
                "implemented": False,
            }
        )
    return summary
