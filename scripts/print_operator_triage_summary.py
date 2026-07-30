#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.operator_triage_queue import (
    build_operator_triage_summary,
    render_operator_triage_queue_markdown,
)


def main() -> int:
    with SessionLocal() as session:
        summary = build_operator_triage_summary(session, get_settings())
    print(render_operator_triage_queue_markdown(summary))
    print("No persistent state, Procore data, or external system was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
