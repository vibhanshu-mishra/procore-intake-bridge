#!/usr/bin/env python3
from app.config import get_settings
from app.services.infra_security_review import (
    build_infra_security_review_report,
    render_storage_boundary_map_markdown,
)


def main() -> int:
    print(
        render_storage_boundary_map_markdown(build_infra_security_review_report(get_settings())),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
