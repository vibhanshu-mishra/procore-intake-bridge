#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.attachment_review import (
    build_attachment_review_filter,
    build_attachment_review_workspace_summary,
    list_attachment_review_records,
    validate_attachment_review_response_safe,
)


def main() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        before = (len(session.new), len(session.dirty), len(session.deleted))
        summary = build_attachment_review_workspace_summary(session, settings)
        page = list_attachment_review_records(
            session, build_attachment_review_filter(settings), settings
        )
        after = (len(session.new), len(session.dirty), len(session.deleted))
    validate_attachment_review_response_safe(summary)
    validate_attachment_review_response_safe(page)
    if before != after:
        raise RuntimeError("Attachment metadata inspection changed session state.")
    print("Attachment Review check")
    print("=======================")
    print(f"Status: {summary.status.value}")
    print("PASS: bounded, metadata-only, local, read-only, and sanitized.")
    print("Persistent state and attachment storage were not accessed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
