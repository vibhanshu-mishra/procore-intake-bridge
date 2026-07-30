#!/usr/bin/env python3
"""Report optional cloud-storage posture without object or network operations."""

import argparse
import json

from app.config import get_settings
from app.schemas.storage import CloudStorageProviderKind
from app.services.storage import build_cloud_storage_provider_health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=[kind.value for kind in CloudStorageProviderKind],
        help="Limit the offline report to one provider.",
    )
    args = parser.parse_args()
    settings = get_settings()
    kinds = (
        [CloudStorageProviderKind(args.provider)]
        if args.provider
        else list(CloudStorageProviderKind)
    )
    print(
        json.dumps(
            {
                "providers": [
                    build_cloud_storage_provider_health(kind, settings).model_dump(
                        mode="json"
                    )
                    for kind in kinds
                ],
                "health_network_check_attempted": False,
                "object_operation_attempted": False,
                "external_calls": False,
                "contents_exposed": False,
                "bucket_names_exposed": False,
                "object_keys_exposed": False,
                "credentials_exposed": False,
                "signed_urls_exposed": False,
                "private_paths_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
