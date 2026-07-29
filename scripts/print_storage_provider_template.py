#!/usr/bin/env python3
import json


def main() -> int:
    print(
        json.dumps(
            {
                "local_provider": {
                    "provider": "local",
                    "root_ref": "LOCAL_STORAGE_ROOT_REF_PLACEHOLDER",
                    "object_ref": "OBJECT_REF_PLACEHOLDER_ATTACHMENT_MANIFEST",
                    "stored_files_included": False,
                },
                "cloud_providers": {
                    "kinds": ["s3", "azure_blob", "gcs"],
                    "optional": True,
                    "enabled_by_default": False,
                    "bucket_names_included": False,
                    "endpoints_included": False,
                    "external_calls": False,
                    "presigned_urls": False,
                },
                "file_contents_exposed": False,
                "local_paths_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
