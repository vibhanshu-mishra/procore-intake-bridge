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
        description="Validate an evidence review metadata manifest locally and offline."
    )
    parser.add_argument("manifest")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--strict-review", action="store_true")
    args = parser.parse_args()
    try:
        manifest = EvidenceReviewManifest.model_validate_json(
            Path(args.manifest).read_text()
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Evidence review invalid: unreadable, malformed, or unsupported local JSON.")
        return 2
    report = build_evidence_review_report(manifest, get_settings())
    print(
        json.dumps(
            sanitize_evidence_review_value(report.model_dump(mode="json")),
            indent=2,
            sort_keys=True,
        )
    )
    if args.strict and report.blocking_findings_count:
        return 1
    if args.strict_review and (
        report.summary.needs_review_items
        or report.summary.renewal_required_items
        or report.summary.blocked_items
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
