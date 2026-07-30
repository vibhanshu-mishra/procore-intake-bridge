#!/usr/bin/env python3

from app.config import Settings
from app.services.sandbox_smoke_ux import (
    build_sandbox_smoke_ux_plan,
    render_sandbox_smoke_preflight,
)


def main() -> int:
    plan = build_sandbox_smoke_ux_plan(Settings())
    print(render_sandbox_smoke_preflight(plan), end="")
    return 1 if any(item.fail_level for item in plan.checklist.findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
