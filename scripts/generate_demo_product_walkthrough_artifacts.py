#!/usr/bin/env python3
import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.demo_product_walkthrough import (
    build_demo_product_walkthrough_report,
    write_demo_product_walkthrough_artifacts,
)


def _generate(output_root: Path) -> int:
    report = build_demo_product_walkthrough_report(get_settings())
    result = write_demo_product_walkthrough_artifacts(report, output_root)
    print(result.model_dump_json(indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ignored, fake-data-only Demo walkthrough artifacts."
    )
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    if args.temporary:
        with tempfile.TemporaryDirectory(
            prefix="procore-intake-bridge-demo-product-", dir="/tmp"
        ) as directory:
            return _generate(Path(directory))
    settings = get_settings()
    return _generate(args.output_root or settings.demo_walkthrough_output_root)


if __name__ == "__main__":
    raise SystemExit(main())
