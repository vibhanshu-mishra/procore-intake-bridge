#!/usr/bin/env python3
from app.config import get_settings
from app.services.data_policy_review import (
    build_data_policy_review_report,
    render_redaction_boundary_map_markdown,
)


def main() -> int:
    print(
        render_redaction_boundary_map_markdown(build_data_policy_review_report(get_settings())),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
