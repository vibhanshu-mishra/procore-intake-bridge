#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.customer_deployment import CustomerDeploymentProfile
from app.services.customer_deployment import (
    CustomerDeploymentBlockedError,
    write_customer_deployment_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized, local-only customer deployment planning artifacts."
    )
    parser.add_argument("profile")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        profile = CustomerDeploymentProfile.model_validate_json(
            Path(args.profile).read_text()
        )
        result = write_customer_deployment_artifacts(
            profile,
            args.output_root or settings.customer_profile_output_root,
            settings,
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Customer artifact generation blocked: profile is unreadable or invalid.")
        return 2
    except CustomerDeploymentBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
