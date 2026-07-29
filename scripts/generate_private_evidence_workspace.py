#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.private_evidence import EvidenceManifest
from app.services.private_evidence import (
    PrivateEvidenceBlockedError,
    write_private_evidence_workspace,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a sanitized local private-evidence workspace scaffold."
    )
    parser.add_argument("manifest")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        manifest = EvidenceManifest.model_validate_json(Path(args.manifest).read_text())
        result = write_private_evidence_workspace(
            manifest,
            args.output_root or settings.private_evidence_output_root,
            settings,
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Evidence workspace generation blocked: manifest is unreadable or invalid.")
        return 2
    except PrivateEvidenceBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
