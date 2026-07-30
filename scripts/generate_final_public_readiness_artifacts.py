#!/usr/bin/env python3
"""Generate ignored final-readiness artifacts without live operations."""

import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.final_public_readiness import (
    build_final_public_readiness_report,
    write_final_public_readiness_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root", type=Path, default=Path("final-readiness-output")
    )
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    try:
        report = build_final_public_readiness_report(get_settings())
        if args.temporary:
            with tempfile.TemporaryDirectory(
                prefix="procore-intake-bridge-final-readiness-", dir="/tmp"
            ) as directory:
                result = write_final_public_readiness_artifacts(
                    report, Path(directory)
                )
                print(result.model_dump_json(indent=2))
        else:
            result = write_final_public_readiness_artifacts(report, args.output_root)
            print(result.model_dump_json(indent=2))
    except Exception:
        print("Final readiness artifact generation blocked; details were suppressed.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
