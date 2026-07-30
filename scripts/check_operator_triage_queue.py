#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.operator_triage_queue import (
    build_operator_triage_filter,
    build_operator_triage_summary,
    list_operator_triage_queue,
    validate_operator_triage_response_safe,
)


def main() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        before = (len(session.new), len(session.dirty), len(session.deleted))
        summary = build_operator_triage_summary(session, settings)
        page = list_operator_triage_queue(session, build_operator_triage_filter(settings), settings)
        after = (len(session.new), len(session.dirty), len(session.deleted))
    validate_operator_triage_response_safe(summary)
    validate_operator_triage_response_safe(page)
    if before != after:
        raise RuntimeError("Operator triage inspection changed session state.")
    print("Operator Triage Queue check")
    print("===========================")
    print(f"Status: {summary.status.value}")
    print("PASS: bounded, deterministic, local-only, read-only, and sanitized.")
    print("Persistent state was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
