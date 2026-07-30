#!/usr/bin/env python3
"""Run a manually gated PostgreSQL migration-status check; never migrate."""

import json

from app.config import get_settings
from app.services.database_runtime import (
    DatabaseRuntimeError,
    run_postgres_migration_status_check,
)


def main() -> int:
    try:
        result = run_postgres_migration_status_check(get_settings())
    except DatabaseRuntimeError as exc:
        print(json.dumps({"status": "refused", "message": str(exc), "external_calls": False}))
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
