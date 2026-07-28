#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.security.admin_access import (
    effective_admin_auth_mode,
    get_admin_auth_config_summary,
    primary_admin_ref,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check sanitized admin-auth posture without printing tokens."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when the configured environment has unsafe admin auth.",
    )
    args = parser.parse_args()
    settings = get_settings()
    summary = get_admin_auth_config_summary(settings)
    print(summary.model_dump_json(indent=2))
    mode = effective_admin_auth_mode(settings)
    unsafe = (
        (settings.environment in {"staging", "production"} and mode != "token_required")
        or (mode == "token_required" and not primary_admin_ref(settings))
        or (
            mode == "token_required"
            and summary.provider_health_status != "healthy"
        )
        or (
            settings.environment in {"staging", "production"}
            and not settings.admin_auth_protect_deployment_routes
        )
        or mode == "invalid"
    )
    return 1 if args.strict and unsafe else 0


if __name__ == "__main__":
    raise SystemExit(main())
