#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.config import Settings
from app.services.private_workspace import (
    PrivateWorkspaceBlockedError,
    write_private_workspace,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an ignored placeholder-only workspace.")
    parser.add_argument(
        "--mode",
        choices=["sandbox", "pilot", "sandbox_and_pilot"],
        default="sandbox_and_pilot",
    )
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    try:
        result = write_private_workspace(
            args.mode,
            args.output_root or settings.private_workspace_root,
            overwrite=args.overwrite,
        )
    except (PrivateWorkspaceBlockedError, OSError) as exc:
        print(f"Private workspace initialization blocked: {exc}")
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
