#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.intake_review_workspace import (
    build_intake_review_filter,
    build_intake_review_workspace_summary,
    list_intake_review_records,
    validate_intake_review_response_safe,
)


def main() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        summary = build_intake_review_workspace_summary(session, settings)
        page = list_intake_review_records(
            session, build_intake_review_filter(settings), settings
        )
    validate_intake_review_response_safe(summary)
    validate_intake_review_response_safe(page)
    print("Intake Review Workspace check")
    print("=============================")
    print(f"Status: {summary.status.value}")
    print(f"Local records inspected: {len(page.items)}")
    print("PASS: local-only, read-only, bounded, and sanitized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
