#!/usr/bin/env python3
"""Inspect final public repository readiness without live operations."""

from app.config import get_settings
from app.services.final_public_readiness import (
    build_final_public_readiness_report,
    render_final_public_readiness_markdown,
    validate_final_public_readiness_report_safe,
)


def main() -> int:
    try:
        report = build_final_public_readiness_report(get_settings())
        validate_final_public_readiness_report_safe(report)
    except Exception:
        print("Final public readiness audit blocked; details were suppressed.")
        return 2
    print(render_final_public_readiness_markdown(report), end="")
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
