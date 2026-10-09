#!/usr/bin/env python3
from app.config import get_settings
from app.services.infra_security_review import (
    build_infra_security_review_report,
    render_secret_boundary_map_markdown,
)


def main() -> int:
    rendered_boundary_map = render_secret_boundary_map_markdown(
        build_infra_security_review_report(get_settings())
    )
    print(
        f"[INFO] Secret boundary map generated successfully (length={len(rendered_boundary_map)} chars)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
