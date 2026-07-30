#!/usr/bin/env python3

import argparse
import json
import tempfile
from pathlib import Path

from app.services.release_readiness import (
    ReleaseReadinessError,
    build_release_readiness_report,
    write_release_readiness_artifacts,
)


def _generate(output_root: Path) -> int:
    result = write_release_readiness_artifacts(
        build_release_readiness_report(),
        output_root,
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized local release-readiness drafts; publish nothing."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("release-readiness-output"),
    )
    parser.add_argument(
        "--temporary",
        action="store_true",
        help="Generate under a disposable temporary directory and remove it automatically.",
    )
    args = parser.parse_args()
    try:
        if args.temporary:
            with tempfile.TemporaryDirectory(prefix="release-readiness-check-") as directory:
                return _generate(Path(directory) / "release-readiness-output")
        return _generate(args.output_root)
    except (ReleaseReadinessError, FileExistsError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
