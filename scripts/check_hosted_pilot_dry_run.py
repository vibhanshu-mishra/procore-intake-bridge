#!/usr/bin/env python3
"""Validate a hosted pilot dry-run profile without reading linked evidence."""

import argparse
from pathlib import Path

from app.config import get_settings
from app.schemas.hosted_pilot_dry_run import HostedPilotDryRunProfile
from app.services.hosted_pilot_dry_run import build_hosted_pilot_dry_run_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        profile = HostedPilotDryRunProfile.model_validate_json(
            args.profile.read_text(encoding="utf-8")
        )
        report = build_hosted_pilot_dry_run_report(profile, get_settings())
    except Exception:
        print("Hosted pilot dry-run validation blocked; details were suppressed.")
        return 2
    print(report.model_dump_json(indent=2))
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
