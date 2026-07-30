#!/usr/bin/env python3
"""Generate ignored placeholder-only Sandbox evidence-linkage artifacts."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.sandbox_evidence_linkage import SandboxEvidenceLinkageProfile
from app.services.sandbox_evidence_linkage import (
    SandboxEvidenceLinkageBlockedError,
    write_sandbox_evidence_linkage_artifacts,
)


def _generate(profile_path: Path, output_root: Path) -> int:
    try:
        profile = SandboxEvidenceLinkageProfile.model_validate_json(
            profile_path.read_text(encoding="utf-8")
        )
        result = write_sandbox_evidence_linkage_artifacts(
            profile,
            output_root,
            get_settings(),
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Sandbox evidence artifact generation blocked: profile is unreadable or invalid.")
        return 2
    except SandboxEvidenceLinkageBlockedError as exc:
        print(str(exc))
        return 2
    print(result.model_dump_json(indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    profile_path = Path(args.profile)
    if args.temporary:
        with TemporaryDirectory() as temporary:
            return _generate(profile_path, Path(temporary) / "sandbox-evidence-output")
    return _generate(
        profile_path,
        args.output_root or get_settings().sandbox_evidence_linkage_output_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
