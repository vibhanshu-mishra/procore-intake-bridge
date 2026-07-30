#!/usr/bin/env python3
import json
import re
from pathlib import Path

TARGETS = [
    Path(".env.example"),
    Path("examples/customer-deployments/example_customer_profile.json"),
    Path("examples/private-workspace/example_workspace_manifest.json"),
    Path("examples/cloud-secret-providers/aws_secret_refs.example.json"),
    Path("examples/cloud-secret-providers/azure_secret_refs.example.json"),
    Path("examples/cloud-secret-providers/gcp_secret_refs.example.json"),
]
UNSAFE = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:postgres|mysql|mongodb)://|"
    r"https?://\S+[?&](?:signature|token|expires)=|"
    r"\barn:aws[a-z-]*:secretsmanager:|"
    r"https://[a-z0-9-]+\.vault\.azure\.net|"
    r"\bprojects/[^/\s]+/secrets/[^/\s]+|"
    r"BEGIN [A-Z ]*PRIVATE KEY|"
    r'"(?:private_key|client_email)"\s*:)'
)


def main() -> int:
    findings = 0
    checked = 0
    for path in TARGETS:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            findings += 1
            continue
        checked += 1
        if UNSAFE.search(text):
            findings += 1
    print(
        json.dumps(
            {
                "files_checked": checked,
                "blocking_findings_count": findings,
                "refs_only": findings == 0,
                "values_resolved": False,
                "values_exposed": False,
                "external_calls": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
