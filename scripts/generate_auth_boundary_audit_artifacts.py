#!/usr/bin/env python3
import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.auth_boundary_audit import (
    build_auth_boundary_audit_report,
    write_auth_boundary_audit_artifacts,
)


def _generate(root: Path) -> int:
    result = write_auth_boundary_audit_artifacts(
        build_auth_boundary_audit_report(get_settings()), root
    )
    print(result.model_dump_json(indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sanitized auth-boundary artifacts.")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(
            prefix="procore-intake-bridge-auth-boundary-", dir="/tmp"
        ) as directory:
            return _generate(Path(directory))
    settings = get_settings()
    return _generate(args.output_root or settings.auth_boundary_audit_output_root)


if __name__ == "__main__":
    raise SystemExit(main())
