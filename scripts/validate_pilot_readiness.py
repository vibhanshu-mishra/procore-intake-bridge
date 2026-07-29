#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.pilot_readiness import (
    PilotReadinessDecision,
    PilotReadinessProfile,
)
from app.services.pilot_readiness import (
    build_pilot_readiness_report,
    sanitize_pilot_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a local placeholder pilot profile without external calls."
    )
    parser.add_argument("profile")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--strict-review", action="store_true")
    args = parser.parse_args()
    try:
        profile = PilotReadinessProfile.model_validate_json(
            Path(args.profile).read_text()
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Pilot readiness profile is unreadable or invalid.")
        return 2
    report = build_pilot_readiness_report(profile, get_settings())
    print(json.dumps(
        sanitize_pilot_value(report.model_dump(mode="json")),
        indent=2,
        sort_keys=True,
    ))
    if args.strict and report.decision in {
        PilotReadinessDecision.NO_GO,
        PilotReadinessDecision.BLOCKED,
    }:
        return 1
    if args.strict_review and report.decision == PilotReadinessDecision.NEEDS_REVIEW:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
