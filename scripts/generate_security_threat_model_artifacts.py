#!/usr/bin/env python3
import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.security_threat_model import (
    build_security_threat_model_report,
    write_security_threat_model_artifacts,
)


def _generate(root: Path) -> int:
    result = write_security_threat_model_artifacts(
        build_security_threat_model_report(get_settings()), root
    )
    print(result.model_dump_json(indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sanitized offline threat-model files.")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(
            prefix="procore-intake-bridge-security-threat-model-", dir="/tmp"
        ) as directory:
            return _generate(Path(directory))
    settings = get_settings()
    return _generate(args.output_root or settings.security_threat_model_output_root)


if __name__ == "__main__":
    raise SystemExit(main())
