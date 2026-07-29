#!/usr/bin/env python3
import json

from app.config import get_settings
from app.services.database_readiness import build_database_readiness_report


def main() -> int:
    report = build_database_readiness_report(get_settings())
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
