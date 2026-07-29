#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.config import Settings
from app.services.private_workspace import (
    PrivateWorkspaceBlockedError,
    validate_existing_private_workspace,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a private workspace or fake manifest.")
    parser.add_argument("target", nargs="?", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    try:
        report = validate_existing_private_workspace(
            args.target or settings.private_workspace_root, settings
        )
    except PrivateWorkspaceBlockedError as exc:
        print(f"Private workspace validation blocked: {exc}")
        return 2
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    return 1 if args.strict and not report.valid else 0


if __name__ == "__main__":
    raise SystemExit(main())
