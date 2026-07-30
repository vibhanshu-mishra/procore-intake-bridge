#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.intake_lifecycle import build_lifecycle_summary


def main() -> int:
    with SessionLocal() as session:
        summary = build_lifecycle_summary(session, get_settings())
    print("Intake lifecycle summary")
    print("========================")
    print(f"Enabled: {str(summary.enabled).lower()}")
    print(f"Local states: {summary.total_states}")
    print(f"Local events: {summary.total_events}")
    for status, count in sorted(summary.counts_by_status.items()):
        print(f"{status.value}: {count}")
    print(summary.message)
    print("No Procore or external calls were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
