#!/usr/bin/env python3

from app.schemas.release_readiness import ReleaseReadinessStatus
from app.services.release_readiness import (
    build_release_readiness_report,
    render_release_readiness_markdown,
)


def main() -> int:
    report = build_release_readiness_report()
    print(render_release_readiness_markdown(report), end="")
    return 1 if report.status == ReleaseReadinessStatus.BLOCKED else 0


if __name__ == "__main__":
    raise SystemExit(main())
