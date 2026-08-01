#!/usr/bin/env python3
import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.data_policy_review import (
    build_data_policy_review_report,
    write_data_policy_review_artifacts,
)


def _generate(root: Path) -> int:
    result = write_data_policy_review_artifacts(
        build_data_policy_review_report(get_settings()), root
    )
    print(result.model_dump_json(indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sanitized data policy review artifacts.")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(
            prefix="procore-intake-bridge-data-policy-", dir="/tmp"
        ) as directory:
            return _generate(Path(directory))
    settings = get_settings()
    return _generate(args.output_root or settings.data_policy_review_output_root)


if __name__ == "__main__":
    raise SystemExit(main())
