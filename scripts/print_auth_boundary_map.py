#!/usr/bin/env python3
from app.config import get_settings
from app.services.auth_boundary_audit import (
    build_auth_boundary_audit_report,
    render_auth_boundary_map_markdown,
)


def main() -> int:
    report = build_auth_boundary_audit_report(get_settings())
    print(render_auth_boundary_map_markdown(report), end="")
    return 0 if report.status.value == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
