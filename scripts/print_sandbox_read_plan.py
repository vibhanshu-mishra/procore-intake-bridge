#!/usr/bin/env python3
"""Print the offline bounded Sandbox read-validation plan."""

from app.config import get_settings
from app.services.sandbox_read_validation import build_sandbox_read_validation_plan


def main() -> int:
    report = build_sandbox_read_validation_plan(get_settings())
    print("Sandbox read-validation plan — OFFLINE ONLY")
    print("============================================")
    print(
        "Tools: "
        + ", ".join(tool.value for tool in report.selected_tools)
        + f"; projects<={report.max_projects}; items/tool<={report.max_items_per_tool}; "
        + f"pages<={report.max_pages}."
    )
    print(
        "List and optional detail reads are bounded. Updated-since filtering is represented "
        "for review where supported."
    )
    print(
        "No credentials are resolved and no Procore, attachment, webhook, database, "
        "storage, or external call is attempted."
    )
    print(
        "The separate `make sandbox-read-validation` command is live, manually gated, "
        "and never part of quality or default workflows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
