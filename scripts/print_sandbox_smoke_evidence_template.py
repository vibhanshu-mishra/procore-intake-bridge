#!/usr/bin/env python3

from app.services.sandbox_smoke_ux import render_sandbox_smoke_evidence_template


def main() -> int:
    print(render_sandbox_smoke_evidence_template(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
