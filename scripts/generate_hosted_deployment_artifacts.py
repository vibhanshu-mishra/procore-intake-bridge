#!/usr/bin/env python3
"""Generate ignored local hosted-template artifacts; perform no deployment."""

import argparse
import tempfile
from pathlib import Path

from app.schemas.hosted_deployment_templates import HostedDeploymentTemplateProfile
from app.services.hosted_deployment_templates import write_hosted_deployment_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=Path("hosted-deployment-output")
    )
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    try:
        profile = HostedDeploymentTemplateProfile.model_validate_json(
            args.profile.read_text(encoding="utf-8")
        )
        if args.temporary:
            with tempfile.TemporaryDirectory(
                prefix="procore-intake-bridge-hosted-deployment-",
                dir="/tmp",
            ) as directory:
                result = write_hosted_deployment_artifacts(profile, Path(directory))
                print(result.model_dump_json(indent=2))
        else:
            result = write_hosted_deployment_artifacts(profile, args.output_root)
            print(result.model_dump_json(indent=2))
    except Exception:
        print("Hosted deployment artifact generation blocked; details were suppressed.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
