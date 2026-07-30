#!/usr/bin/env python3
from app.config import get_settings
from app.services.demo_product_walkthrough import (
    build_demo_product_walkthrough_report,
    validate_demo_product_walkthrough_report_safe,
)


def main() -> int:
    report = build_demo_product_walkthrough_report(get_settings())
    validate_demo_product_walkthrough_report_safe(report)
    print("Demo Product Walkthrough check")
    print("==============================")
    print(f"Status: {report.status.value}")
    print(f"Steps ready: {report.steps_ready}/{report.steps_total}")
    if report.steps_needing_review:
        print("Review required: one or more public Demo components are incomplete.")
        return 1
    print("PASS: fake-data-only, offline, sanitized, and complete.")
    print("No database, Procore, external, deployment, or release operation was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
