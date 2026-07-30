#!/usr/bin/env python3
"""Report cloud secret-provider posture without resolving secrets or using network."""

import argparse
import json

from app.config import get_settings
from app.schemas.secrets import CloudSecretProviderKind
from app.services.secrets import build_cloud_secret_provider_health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=[kind.value for kind in CloudSecretProviderKind],
        help="Limit the offline readiness report to one provider.",
    )
    args = parser.parse_args()
    settings = get_settings()
    kinds = (
        [CloudSecretProviderKind(args.provider)]
        if args.provider
        else list(CloudSecretProviderKind)
    )
    health = [
        build_cloud_secret_provider_health(kind, settings).model_dump(mode="json")
        for kind in kinds
    ]
    print(
        json.dumps(
            {
                "providers": health,
                "health_network_check_attempted": False,
                "secret_resolution_attempted": False,
                "external_calls": False,
                "value_exposed": False,
                "resource_names_exposed": False,
                "credentials_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
