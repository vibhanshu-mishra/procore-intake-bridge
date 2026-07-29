#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.pilot_approval import PilotApprovalPacket, PilotApprovalStatus
from app.services.pilot_approval import (
    build_pilot_approval_validation_report,
    sanitize_pilot_approval_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a local placeholder pilot approval packet offline."
    )
    parser.add_argument("packet")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--strict-review", action="store_true")
    args = parser.parse_args()
    try:
        packet = PilotApprovalPacket.model_validate_json(Path(args.packet).read_text())
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Pilot approval packet invalid: unreadable, malformed, or unsupported JSON.")
        return 2
    report = build_pilot_approval_validation_report(packet, get_settings())
    print(
        json.dumps(
            sanitize_pilot_approval_value(report.model_dump(mode="json")),
            indent=2,
            sort_keys=True,
        )
    )
    if args.strict and report.evaluation == PilotApprovalStatus.BLOCKED:
        return 1
    if args.strict_review and report.evaluation == PilotApprovalStatus.NEEDS_REVIEW:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
