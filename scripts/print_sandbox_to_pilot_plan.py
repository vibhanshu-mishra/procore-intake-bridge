#!/usr/bin/env python3
from app.config import get_settings
from app.services.sandbox_pilot_flow import (
    build_default_flow_template,
    build_sandbox_pilot_flow_report,
    render_sandbox_to_pilot_plan,
)


def main() -> int:
    profile = build_default_flow_template("demo", get_settings())
    print(
        render_sandbox_to_pilot_plan(
            profile, build_sandbox_pilot_flow_report(profile, get_settings())
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
