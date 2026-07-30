#!/usr/bin/env python3
"""Print an offline, sanitized PostgreSQL runtime posture report."""

import json

from app.config import get_settings
from app.services.database_runtime import build_postgres_runtime_report


def main() -> int:
    report = build_postgres_runtime_report(get_settings())
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
