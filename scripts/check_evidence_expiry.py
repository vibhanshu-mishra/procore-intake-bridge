#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.evidence_review import EvidenceReviewManifest
from app.services.evidence_review import (
    build_evidence_review_report,
    sanitize_evidence_review_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check placeholder evidence expiry metadata locally without notifications."
    )
    parser.add_argument("manifest")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        manifest = EvidenceReviewManifest.model_validate_json(
            Path(args.manifest).read_text()
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Evidence expiry check blocked: manifest is unreadable or invalid.")
        return 2
    report = build_evidence_review_report(manifest, get_settings())
    payload = {
        "profile_name": report.profile_name,
        "summary": report.summary.model_dump(mode="json"),
        "external_calls": False,
        "notifications_sent": False,
        "values_exposed": False,
    }
    print(json.dumps(sanitize_evidence_review_value(payload), indent=2, sort_keys=True))
    if args.strict and (
        report.summary.expired_items
        or report.summary.renewal_required_items
        or report.summary.blocked_items
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
