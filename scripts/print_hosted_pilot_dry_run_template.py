#!/usr/bin/env python3
"""Print a placeholder-only hosted pilot dry-run profile."""

from app.config import get_settings
from app.services.hosted_pilot_dry_run import (
    build_default_hosted_pilot_dry_run_profile,
)


def main() -> int:
    profile = build_default_hosted_pilot_dry_run_profile(get_settings())
    print(profile.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
