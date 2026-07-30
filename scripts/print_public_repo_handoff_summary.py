#!/usr/bin/env python3
"""Print the public repository maintainer handoff summary."""

from app.config import get_settings
from app.services.final_public_readiness import (
    build_final_public_readiness_report,
    render_maintainer_handoff_summary,
)


def main() -> int:
    report = build_final_public_readiness_report(get_settings())
    print(render_maintainer_handoff_summary(report), end="")
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
