#!/usr/bin/env python3
"""Print an offline PostgreSQL migration checklist; execute nothing."""

from app.config import get_settings
from app.services.database_runtime import (
    build_postgres_migration_execution_plan,
    render_postgres_migration_execution_plan_markdown,
)


def main() -> int:
    plan = build_postgres_migration_execution_plan(get_settings())
    print(render_postgres_migration_execution_plan_markdown(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
