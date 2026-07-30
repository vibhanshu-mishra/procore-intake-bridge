#!/usr/bin/env python3

from app.config import Settings
from app.services.sandbox_smoke_ux import (
    build_sandbox_smoke_ux_plan,
    render_sandbox_smoke_explanation,
)


def main() -> int:
    print(render_sandbox_smoke_explanation(build_sandbox_smoke_ux_plan(Settings())), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
