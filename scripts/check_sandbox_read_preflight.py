#!/usr/bin/env python3
"""Run the offline Sandbox read-validation preflight."""

from app.config import get_settings
from app.services.sandbox_read_validation import build_sandbox_read_preflight


def main() -> int:
    report = build_sandbox_read_preflight(get_settings())
    print("Sandbox read-validation preflight — OFFLINE ONLY")
    print("=================================================")
    print(f"Status: {report.status.value}")
    for requirement in report.requirements:
        print(f"- {requirement.name}: {requirement.status.value}")
    print(
        "This check resolves no credentials, reads no private files or database rows, "
        "and makes no Procore or external calls."
    )
    return 2 if report.status.value == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
