#!/usr/bin/env python3
"""Compare conceptual hosted platform templates without external calls."""

import json

from app.schemas.hosted_deployment_templates import HostedDeploymentPlatform


def main() -> int:
    rows = [
        {
            "platform": platform.value,
            "template_only": True,
            "private_adaptation_required": True,
            "cloud_calls": False,
            "deployment_automation": False,
            "production_review_required": True,
        }
        for platform in HostedDeploymentPlatform
    ]
    print(json.dumps({"platforms": rows, "deployment_executed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
