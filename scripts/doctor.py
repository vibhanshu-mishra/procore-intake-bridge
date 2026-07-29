#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.config import Settings
from app.services.usage_modes import (
    UsageModeBlockedError,
    build_usage_mode_doctor_report,
    render_usage_mode_report_markdown,
    write_usage_mode_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local three-mode readiness doctor.")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    try:
        settings = Settings()
        report = build_usage_mode_doctor_report(settings)
        print(render_usage_mode_report_markdown(report), end="")
        if args.output_root:
            result = write_usage_mode_report(report, args.output_root)
            print(f"Report written under {result.output_directory}/")
        return 0
    except UsageModeBlockedError as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
