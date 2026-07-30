#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.operator_export_pack import (
    build_operator_export_combined_packet,
    build_operator_export_filter,
    render_operator_export_csv_sections,
    render_operator_export_json,
    render_operator_export_markdown,
    validate_operator_export_safe,
)


def main() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        before = (len(session.new), len(session.dirty), len(session.deleted))
        packet = build_operator_export_combined_packet(
            session, build_operator_export_filter(settings), settings
        )
        after = (len(session.new), len(session.dirty), len(session.deleted))
    validate_operator_export_safe(packet)
    render_operator_export_json(packet)
    render_operator_export_markdown(packet)
    render_operator_export_csv_sections(packet)
    if before != after:
        raise RuntimeError("Operator export inspection changed session state.")
    print("Operator Export Pack check")
    print("==========================")
    print(f"Status: {packet.metadata.status.value}")
    print("PASS: bounded JSON, Markdown, and CSV summaries are sanitized.")
    print("No artifact, persistent state, file source, or external system was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
