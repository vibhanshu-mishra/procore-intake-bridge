#!/usr/bin/env python3
"""Print the placeholder-only Sandbox evidence-linkage profile."""

from app.config import get_settings
from app.services.sandbox_evidence_linkage import build_default_sandbox_evidence_profile


def main() -> int:
    profile = build_default_sandbox_evidence_profile(get_settings())
    print(profile.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
