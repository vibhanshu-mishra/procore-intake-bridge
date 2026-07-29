#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.customer_deployment import CustomerDeploymentProfile
from app.services.customer_deployment import (
    build_customer_deployment_readiness_report,
    sanitize_customer_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a local customer deployment planning profile offline."
    )
    parser.add_argument("profile")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        profile = CustomerDeploymentProfile.model_validate_json(
            Path(args.profile).read_text()
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Customer profile invalid: unreadable or malformed local JSON.")
        return 2
    report = build_customer_deployment_readiness_report(profile, get_settings())
    print(json.dumps(
        sanitize_customer_value(report.model_dump(mode="json")),
        indent=2,
        sort_keys=True,
    ))
    return int(args.strict and report.blocking_findings_count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
