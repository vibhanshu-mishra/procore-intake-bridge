#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.services.support_bundle import (
    SupportBundleBlockedError,
    check_support_bundle_redaction,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check local support bundle files for unsafe material."
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        report = check_support_bundle_redaction(args.path)
    except SupportBundleBlockedError as exc:
        print(str(exc))
        return 2
    print(report.model_dump_json(indent=2))
    return int(not report.safe)


if __name__ == "__main__":
    raise SystemExit(main())
