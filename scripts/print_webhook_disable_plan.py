#!/usr/bin/env python3
"""Print the offline webhook disable checklist."""

from app.config import get_settings
from app.services.https_webhook_planning import (
    build_default_https_webhook_profile,
    build_https_webhook_report,
    render_webhook_disable_plan,
)


def main() -> int:
    settings = get_settings()
    profile = build_default_https_webhook_profile(settings)
    report = build_https_webhook_report(profile, settings)
    print(render_webhook_disable_plan(profile, report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
