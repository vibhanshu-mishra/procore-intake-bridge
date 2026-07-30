#!/usr/bin/env python3

from app.services.release_readiness import (
    build_release_readiness_report,
    render_maintainer_review_checklist,
)


def main() -> int:
    print(render_maintainer_review_checklist(build_release_readiness_report()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
