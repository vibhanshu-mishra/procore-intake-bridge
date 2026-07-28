#!/usr/bin/env python3
import argparse
import json

from app.config import get_settings
from app.services.startup_checks import StartupCheckError, run_startup_checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sanitized startup safety checks.")
    parser.add_argument("--strict", action="store_true", help="Fail if any blockers exist.")
    args = parser.parse_args()
    try:
        report = run_startup_checks(get_settings())
    except StartupCheckError as exc:
        print(str(exc))
        return 1
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    return 1 if args.strict and report.blocking_findings_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
