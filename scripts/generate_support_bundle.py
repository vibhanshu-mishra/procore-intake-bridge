#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.main import app
from app.services.support_bundle import (
    SupportBundleBlockedError,
    build_support_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a sanitized local support bundle without external calls."
    )
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        result = build_support_bundle(
            settings,
            app=app,
            output_root=args.output_root or settings.support_bundle_output_root,
        )
    except SupportBundleBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
