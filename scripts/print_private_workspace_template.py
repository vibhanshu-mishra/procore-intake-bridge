#!/usr/bin/env python3
from app.config import Settings
from app.services.private_workspace import build_private_workspace_manifest


def main() -> int:
    manifest = build_private_workspace_manifest("sandbox_and_pilot", Settings())
    print(manifest.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
