#!/usr/bin/env python3
import argparse
import json

from app.config import get_settings
from app.services.attachment_storage_factory import (
    build_attachment_storage_provider,
    get_attachment_storage_provider_name,
    summarize_attachment_storage_config,
)
from app.services.attachment_storage_provider import AttachmentStorageProviderError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check sanitized attachment-storage posture without external calls."
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    try:
        provider = build_attachment_storage_provider(settings)
        health = (
            provider.health_check().model_dump()
            if settings.attachment_storage_health_check_enabled
            else {"status": "not_checked", "available": None}
        )
    except (AttachmentStorageProviderError, ValueError):
        health = {"status": "misconfigured", "available": False}
    payload = {
        "config": summarize_attachment_storage_config(settings),
        "health": health,
        "external_calls": False,
        "secrets_exposed": False,
        "paths_exposed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    name = get_attachment_storage_provider_name(settings)
    unsafe = (
        not health.get("available", False)
        or name in {"test", "external_placeholder", "disabled"}
        or settings.attachment_storage_max_object_bytes <= 0
        or not settings.attachment_storage_require_safe_keys
        or (
            settings.environment == "production"
            and (
                name == "local"
                or not settings.attachment_fixture_downloads_only
            )
        )
    )
    return 1 if args.strict and unsafe else 0


if __name__ == "__main__":
    raise SystemExit(main())
