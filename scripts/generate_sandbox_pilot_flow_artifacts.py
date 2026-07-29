#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.schemas.sandbox_pilot_flow import FlowProfile
from app.services.sandbox_pilot_flow import write_sandbox_pilot_flow_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("sandbox-pilot-output"))
    args = parser.parse_args()
    try:
        profile = FlowProfile.model_validate_json(args.profile.read_text())
        result = write_sandbox_pilot_flow_artifacts(profile, args.output_root)
    except Exception:
        print("Flow artifact generation blocked; private details were suppressed.")
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
