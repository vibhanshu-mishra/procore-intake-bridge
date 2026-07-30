#!/usr/bin/env python3
import json
import re
from pathlib import Path

TARGETS = [
    Path(".env.example"),
    Path("examples/customer-deployments/example_customer_profile.json"),
    Path("examples/private-workspace/example_workspace_manifest.json"),
    Path("examples/cloud-storage-providers/s3_storage_refs.example.json"),
    Path("examples/cloud-storage-providers/azure_blob_storage_refs.example.json"),
    Path("examples/cloud-storage-providers/gcs_storage_refs.example.json"),
]
UNSAFE = re.compile(
    r"(?i)(https?://\S+[?&](?:signature|signed|token|expires)=|"
    r"(?:s3|gs|azure)://(?![^\s]*placeholder)|"
    r"\barn:aws[a-z-]*:s3:|"
    r"https://[a-z0-9-]+\.blob\.core\.windows\.net|"
    r"\bprojects/[^/\s]+/(?:buckets|locations)/|"
    r"BEGIN [A-Z ]*PRIVATE KEY|"
    r'"(?:private_key|client_email)"\s*:|'
    r"(?:aws_access_key|secret_access_key|private_key)\s*[:=])"
)


def main() -> int:
    checked = 0
    blockers = 0
    for path in TARGETS:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            blockers += 1
            continue
        checked += 1
        blockers += bool(UNSAFE.search(text))
    print(
        json.dumps(
            {
                "files_checked": checked,
                "blocking_findings_count": blockers,
                "object_contents_read": False,
                "bucket_names_exposed": False,
                "local_paths_exposed": False,
                "external_calls": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
