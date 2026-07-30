#!/usr/bin/env python3
"""Print a placeholder-only hosted deployment profile; deploy nothing."""

import argparse

from app.config import get_settings
from app.schemas.hosted_deployment_templates import HostedDeploymentPlatform
from app.services.hosted_deployment_templates import (
    build_default_hosted_deployment_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        choices=[item.value for item in HostedDeploymentPlatform],
        default=HostedDeploymentPlatform.DOCKER_VPS.value,
    )
    args = parser.parse_args()
    profile = build_default_hosted_deployment_profile(args.platform, get_settings())
    print(profile.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
