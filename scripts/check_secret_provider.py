#!/usr/bin/env python3
import argparse
import json

from app.config import get_settings
from app.security.secret_provider_factory import (
    build_secret_provider,
    summarize_secret_provider_config,
)
from app.security.secrets import SecretProviderError
from app.services.secret_inventory import collect_required_secret_refs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check secret-provider posture without printing secret values."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when the provider is unavailable or a required ref is missing.",
    )
    args = parser.parse_args()
    settings = get_settings()
    inventory = collect_required_secret_refs(settings, run_health=True)
    unavailable = False
    if not settings.secret_health_check_enabled:
        health_payload = {
            "provider": settings.secret_provider,
            "status": "disabled",
            "checked_refs_count": 0,
            "present_refs_count": 0,
            "missing_refs_count": 0,
            "refs": [],
            "message": "Provider health checking is disabled by configuration.",
        }
    else:
        try:
            provider = build_secret_provider(settings)
            raw_refs = [
                ref
                for ref in (
                    settings.admin_token_secret_name
                    if settings.admin_require_token
                    else "",
                    settings.webhook_secret_name
                    if settings.require_webhook_signature
                    else "",
                )
                if ref
            ]
            health = provider.health_check(raw_refs)
            health_payload = {
                "provider": health.provider,
                "status": health.status,
                "checked_refs_count": health.checked_refs_count,
                "present_refs_count": health.present_refs_count,
                "missing_refs_count": health.missing_refs_count,
                "refs": [
                    {"masked_ref": item.masked_ref, "status": item.status}
                    for item in health.refs
                ],
                "message": health.message,
            }
            unavailable = health.status not in {"healthy", "degraded"}
        except SecretProviderError:
            health_payload = {
                "provider": settings.secret_provider,
                "status": "unavailable",
                "checked_refs_count": len(inventory),
                "present_refs_count": 0,
                "missing_refs_count": len(inventory),
                "refs": [],
                "message": (
                    "Provider is unavailable or misconfigured; details were suppressed."
                ),
            }
            unavailable = True
    output = {
        "config": summarize_secret_provider_config(settings),
        "health": health_payload,
        "required_refs": [item.model_dump() for item in inventory],
        "values_exposed": False,
    }
    print(json.dumps(output, indent=2))
    missing = health_payload["missing_refs_count"] > 0
    return 1 if args.strict and (unavailable or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
