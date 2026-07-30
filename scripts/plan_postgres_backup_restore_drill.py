#!/usr/bin/env python3
"""Print offline PostgreSQL backup/restore drill checklists; inspect nothing."""

from app.config import get_settings
from app.services.database_runtime import (
    build_postgres_backup_verification_plan,
    build_postgres_restore_drill_plan,
    render_postgres_backup_verification_plan_markdown,
    render_postgres_restore_drill_plan_markdown,
)


def main() -> int:
    settings = get_settings()
    print(render_postgres_backup_verification_plan_markdown(
        build_postgres_backup_verification_plan(settings)
    ))
    print(render_postgres_restore_drill_plan_markdown(
        build_postgres_restore_drill_plan(settings)
    ), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
