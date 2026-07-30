#!/usr/bin/env python3
import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.services.operator_export_pack import (
    build_operator_export_combined_packet,
    build_operator_export_filter,
    write_operator_export_artifacts,
)


def _generate(output_root: Path) -> int:
    settings = get_settings()
    filters = build_operator_export_filter(settings)
    with SessionLocal() as session:
        packet = build_operator_export_combined_packet(session, filters, settings)
    result = write_operator_export_artifacts(packet, output_root, filters.formats)
    print("Operator Export Pack")
    print("====================")
    print(f"Status: {result.status.value}")
    print(f"Output label: {result.output_directory}")
    print(f"Files: {', '.join(result.files)}")
    print("Sanitized local summaries only; no private path is printed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sanitized local operator summaries.")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(
            prefix="procore-intake-bridge-operator-export-",
            dir="/tmp",
        ) as temporary:
            return _generate(Path(temporary))
    settings = get_settings()
    return _generate(args.output_root or settings.export_pack_output_root)


if __name__ == "__main__":
    raise SystemExit(main())
