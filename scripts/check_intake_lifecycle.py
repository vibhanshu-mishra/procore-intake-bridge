#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.schemas.intake_lifecycle import (
    IntakeLifecycleReasonCode,
    IntakeLifecycleStatus,
)
from app.services.intake_lifecycle import (
    build_lifecycle_summary,
    validate_lifecycle_response_safe,
    validate_lifecycle_transition,
)


def main() -> int:
    settings = get_settings()
    validate_lifecycle_transition(
        IntakeLifecycleStatus.NEW,
        IntakeLifecycleStatus.IN_REVIEW,
        IntakeLifecycleReasonCode.INITIAL_REVIEW_STARTED,
        settings,
    )
    with SessionLocal() as session:
        summary = build_lifecycle_summary(session, settings)
    validate_lifecycle_response_safe(summary)
    print("Intake lifecycle check")
    print("======================")
    print(f"Enabled: {str(summary.enabled).lower()}")
    print("PASS: bounded local transition rules and sanitized read-only summary.")
    print("Persistent lifecycle state was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
