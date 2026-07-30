#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.operator_export_pack import (
    build_operator_export_combined_packet,
    build_operator_export_filter,
    render_operator_export_markdown,
)


def main() -> int:
    settings = get_settings()
    with SessionLocal() as session:
        packet = build_operator_export_combined_packet(
            session, build_operator_export_filter(settings), settings
        )
    print(render_operator_export_markdown(packet), end="")
    print("No artifact was written and no external operation was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
