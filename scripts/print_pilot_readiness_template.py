#!/usr/bin/env python3
from pathlib import Path

from app.schemas.pilot_readiness import PilotReadinessProfile


def main() -> int:
    profile = PilotReadinessProfile.model_validate_json(
        Path("examples/pilot-readiness/example_pilot_profile.json").read_text()
    )
    print(profile.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
