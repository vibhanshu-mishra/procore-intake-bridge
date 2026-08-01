#!/usr/bin/env python3
from app.config import get_settings
from app.services.infra_security_review import (
    build_infra_security_review_report,
    render_infra_security_review_markdown,
)


def main() -> int:
    report = build_infra_security_review_report(get_settings())
    print(render_infra_security_review_markdown(report), end="")
    return 1 if report.status.value == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
