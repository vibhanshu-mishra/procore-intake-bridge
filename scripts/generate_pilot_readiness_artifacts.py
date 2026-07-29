#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.pilot_readiness import PilotReadinessProfile
from app.services.pilot_readiness import (
    PilotReadinessBlockedError,
    write_pilot_readiness_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized local pilot readiness planning artifacts."
    )
    parser.add_argument("profile")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        profile = PilotReadinessProfile.model_validate_json(
            Path(args.profile).read_text()
        )
        result = write_pilot_readiness_artifacts(
            profile,
            args.output_root or settings.pilot_readiness_output_root,
            settings,
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Pilot artifact generation blocked: profile is unreadable or invalid.")
        return 2
    except PilotReadinessBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
