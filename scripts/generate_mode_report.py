#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.config import Settings
from app.services.usage_modes import (
    UsageModeBlockedError,
    build_usage_mode_doctor_report,
    write_usage_mode_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a sanitized local mode report.")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    try:
        settings = Settings()
        report = build_usage_mode_doctor_report(settings)
        result = write_usage_mode_report(
            report, args.output_root or settings.mode_report_output_root
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0
    except (UsageModeBlockedError, FileExistsError) as exc:
        print(f"BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
