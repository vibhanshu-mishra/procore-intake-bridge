#!/usr/bin/env python3
"""Print placeholder-only cloud-storage configuration templates."""

import json


def main() -> int:
    print(
        json.dumps(
            {
                "s3": {
                    "enabled": False,
                    "region_ref": "S3_REGION_REF_PLACEHOLDER",
                    "bucket_ref": "S3_BUCKET_REF_PLACEHOLDER",
                    "object_prefix": "S3_OBJECT_PREFIX_PLACEHOLDER",
                },
                "azure_blob": {
                    "enabled": False,
                    "account_ref": "AZURE_STORAGE_ACCOUNT_REF_PLACEHOLDER",
                    "container_ref": "AZURE_BLOB_CONTAINER_REF_PLACEHOLDER",
                    "object_prefix": "AZURE_BLOB_PREFIX_PLACEHOLDER",
                },
                "gcs": {
                    "enabled": False,
                    "project_ref": "GCS_PROJECT_ID_REF_PLACEHOLDER",
                    "bucket_ref": "GCS_BUCKET_REF_PLACEHOLDER",
                    "object_prefix": "GCS_OBJECT_PREFIX_PLACEHOLDER",
                },
                "cloud_network_enabled": False,
                "list_allowed": False,
                "delete_allowed": False,
                "overwrite_allowed": False,
                "presigned_urls_allowed": False,
                "external_calls": False,
                "object_operations_attempted": False,
                "contents_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
