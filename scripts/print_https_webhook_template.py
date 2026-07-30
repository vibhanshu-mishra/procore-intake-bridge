#!/usr/bin/env python3
"""Print a placeholder-only HTTPS/webhook planning profile."""

from app.config import get_settings
from app.services.https_webhook_planning import build_default_https_webhook_profile


def main() -> int:
    print(build_default_https_webhook_profile(get_settings()).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
