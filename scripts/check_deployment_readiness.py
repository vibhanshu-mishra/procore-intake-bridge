#!/usr/bin/env python3
import argparse
import json

from app.config import get_settings
from app.services.deployment_readiness import build_deployment_readiness_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a sanitized deployment readiness report.")
    parser.add_argument("--strict", action="store_true", help="Fail if production has blockers.")
    args = parser.parse_args()
    report = build_deployment_readiness_report(get_settings())
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    return 1 if args.strict and report.blocking_findings_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
