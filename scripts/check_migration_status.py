#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.services.migration_status import build_migration_status_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect sanitized migration status without changing the database."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when migrations are pending or status inspection fails.",
    )
    args = parser.parse_args()
    report = build_migration_status_report(get_settings())
    print(report.model_dump_json(indent=2))
    has_error = any(finding.severity == "error" for finding in report.findings)
    return 1 if args.strict and (report.pending_migration_detected or has_error) else 0


if __name__ == "__main__":
    raise SystemExit(main())
