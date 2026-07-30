#!/usr/bin/env python3
"""Print the local-only mapping from Sandbox refs into Pilot workflows."""

from app.config import get_settings
from app.services.sandbox_evidence_linkage import (
    build_default_sandbox_evidence_profile,
    build_sandbox_evidence_linkage_report,
    render_flow_mapping,
    render_pilot_approval_mapping,
    render_pilot_readiness_mapping,
)


def main() -> int:
    settings = get_settings()
    profile = build_default_sandbox_evidence_profile(settings)
    report = build_sandbox_evidence_linkage_report(profile, settings)
    print(render_pilot_readiness_mapping(profile, report))
    print(render_pilot_approval_mapping(profile, report))
    print(render_flow_mapping(profile, report))
    print(
        "Mappings contain opaque placeholders only. They read no private reports, "
        "make no external calls, and grant no approval."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
