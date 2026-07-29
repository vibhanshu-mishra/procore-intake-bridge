#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.pilot_approval import PilotApprovalPacket, PilotApprovalStatus
from app.services.pilot_approval import (
    build_pilot_approval_validation_report,
    find_pilot_approval_safety_codes,
)

SAFE_GENERATED_FILES = {
    "approval-packet.json",
    "approval-packet.md",
    "approval-summary.md",
    "launch-conditions.md",
    "rollback-conditions.md",
    "risk-acceptance.md",
    "signoff-template.md",
    "manifest.json",
}


def _check_packet(path: Path) -> int:
    try:
        packet = PilotApprovalPacket.model_validate_json(path.read_text())
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Pilot approval safety check failed: unreadable or invalid packet.")
        return 2
    report = build_pilot_approval_validation_report(packet, get_settings())
    if report.evaluation == PilotApprovalStatus.BLOCKED:
        print("Pilot approval safety check failed with sanitized blocking findings.")
        return 1
    print("Pilot approval safety check passed for placeholder packet metadata.")
    return 0


def _check_generated(root: Path) -> int:
    if not root.is_dir() or root == Path("/") or ".." in root.parts:
        print("Pilot approval safety check failed: unsafe or missing directory.")
        return 2
    files = [path for path in root.rglob("*") if path.is_file()]
    if not files or len(files) > 16:
        print("Pilot approval safety check failed: unexpected generated file count.")
        return 1
    if any(path.name not in SAFE_GENERATED_FILES for path in files):
        print("Pilot approval safety check failed: unexpected generated filename.")
        return 1
    try:
        unsafe = any(
            find_pilot_approval_safety_codes(path.read_text()) for path in files
        )
    except (OSError, UnicodeDecodeError):
        print("Pilot approval safety check failed: unreadable generated content.")
        return 1
    if unsafe:
        print("Pilot approval safety check failed: unsafe generated content detected.")
        return 1
    packet_files = [path for path in files if path.name == "approval-packet.json"]
    if len(packet_files) != 1:
        print("Pilot approval safety check failed: packet metadata file is missing.")
        return 1
    return _check_packet(packet_files[0])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a placeholder approval packet or generated local packet directory."
    )
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    return _check_generated(args.target) if args.target.is_dir() else _check_packet(args.target)


if __name__ == "__main__":
    raise SystemExit(main())
