#!/usr/bin/env python3
"""Validate one placeholder-only Sandbox evidence-linkage profile."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.sandbox_evidence_linkage import (
    SandboxEvidenceLinkageProfile,
    SandboxEvidenceStatus,
)
from app.services.sandbox_evidence_linkage import (
    build_sandbox_evidence_linkage_report,
    render_sandbox_evidence_linkage_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    args = parser.parse_args()
    try:
        profile = SandboxEvidenceLinkageProfile.model_validate_json(
            Path(args.profile).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Sandbox evidence linkage blocked: profile is unreadable or invalid.")
        return 2
    report = build_sandbox_evidence_linkage_report(profile, get_settings())
    print(render_sandbox_evidence_linkage_markdown(report))
    return 2 if report.status == SandboxEvidenceStatus.BLOCKED else 0


if __name__ == "__main__":
    raise SystemExit(main())
