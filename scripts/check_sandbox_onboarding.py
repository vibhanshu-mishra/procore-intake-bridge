#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.config import get_settings
from app.schemas.sandbox_pilot_flow import FlowMode, FlowProfile
from app.services.sandbox_pilot_flow import build_sandbox_pilot_flow_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        profile = FlowProfile.model_validate_json(args.profile.read_text())
        if profile.selected_path != FlowMode.SANDBOX:
            raise ValueError
        report = build_sandbox_pilot_flow_report(profile, get_settings())
    except Exception:
        print("Sandbox onboarding check blocked; private details were suppressed.")
        return 2
    print(report.model_dump_json(indent=2))
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
