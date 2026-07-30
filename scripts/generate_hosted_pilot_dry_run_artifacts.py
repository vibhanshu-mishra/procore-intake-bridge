#!/usr/bin/env python3
"""Generate ignored dry-run artifacts without live or private evidence reads."""

import argparse
import tempfile
from pathlib import Path

from app.schemas.hosted_pilot_dry_run import HostedPilotDryRunProfile
from app.services.hosted_pilot_dry_run import write_hosted_pilot_dry_run_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=Path("hosted-pilot-dry-run-output")
    )
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    try:
        profile = HostedPilotDryRunProfile.model_validate_json(
            args.profile.read_text(encoding="utf-8")
        )
        if args.temporary:
            with tempfile.TemporaryDirectory(
                prefix="procore-intake-bridge-hosted-pilot-dry-run-",
                dir="/tmp",
            ) as directory:
                result = write_hosted_pilot_dry_run_artifacts(profile, Path(directory))
                print(result.model_dump_json(indent=2))
        else:
            result = write_hosted_pilot_dry_run_artifacts(profile, args.output_root)
            print(result.model_dump_json(indent=2))
    except Exception:
        print("Hosted pilot dry-run artifact generation blocked; details were suppressed.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
