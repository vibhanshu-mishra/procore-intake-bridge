#!/usr/bin/env python3
from app.config import get_settings
from app.services.database_readiness import (
    build_migration_execution_plan,
    render_migration_execution_plan_markdown,
)


def main() -> int:
    print(render_migration_execution_plan_markdown(
        build_migration_execution_plan(get_settings())
    ), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
