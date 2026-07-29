#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.private_evidence import EvidenceManifest
from app.services.private_evidence import (
    build_evidence_validation_report,
    sanitize_evidence_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a private-evidence metadata manifest locally and offline."
    )
    parser.add_argument("manifest")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        manifest = EvidenceManifest.model_validate_json(Path(args.manifest).read_text())
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Evidence manifest invalid: unreadable, malformed, or contains unsupported fields.")
        return 2
    report = build_evidence_validation_report(manifest, get_settings())
    print(
        json.dumps(
            sanitize_evidence_value(report.model_dump(mode="json")),
            indent=2,
            sort_keys=True,
        )
    )
    return int(args.strict and report.blocking_findings_count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
