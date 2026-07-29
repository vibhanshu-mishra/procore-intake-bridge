#!/usr/bin/env python3
from app.config import get_settings
from app.services.database_readiness import (
    build_backup_restore_plan,
    render_backup_restore_plan_markdown,
)


def main() -> int:
    backup, restore = build_backup_restore_plan(get_settings())
    print(render_backup_restore_plan_markdown(backup), end="")
    print(render_backup_restore_plan_markdown(restore), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
