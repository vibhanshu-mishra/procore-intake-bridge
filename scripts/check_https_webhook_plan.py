#!/usr/bin/env python3
"""Validate an HTTPS/webhook planning profile without external checks."""

import argparse
from pathlib import Path

from app.config import get_settings
from app.schemas.https_webhook_planning import HttpsWebhookPlanningProfile
from app.services.https_webhook_planning import build_https_webhook_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        profile = HttpsWebhookPlanningProfile.model_validate_json(
            args.profile.read_text(encoding="utf-8")
        )
        report = build_https_webhook_report(profile, get_settings())
    except Exception:
        print("HTTPS/webhook planning validation blocked; details were suppressed.")
        return 2
    print(report.model_dump_json(indent=2))
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
