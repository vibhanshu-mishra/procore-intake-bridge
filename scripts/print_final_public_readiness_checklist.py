#!/usr/bin/env python3
"""Print the offline public repository maintainer checklist."""

from app.config import get_settings
from app.services.final_public_readiness import (
    build_final_public_readiness_report,
    render_public_repo_checklist,
)


def main() -> int:
    report = build_final_public_readiness_report(get_settings())
    print(render_public_repo_checklist(report), end="")
    return 2 if report.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
