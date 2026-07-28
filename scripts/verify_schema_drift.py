#!/usr/bin/env python3
import tempfile
from pathlib import Path

from alembic import command

from app.config import get_settings
from app.services.migration_status import (
    compare_metadata_to_migrated_schema,
    get_alembic_config,
)


def main() -> int:
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="procore-schema-drift-") as directory:
        database_path = Path(directory) / "schema-drift.sqlite"
        database_url = f"sqlite:///{database_path}"
        command.upgrade(get_alembic_config(settings, database_url), "head")
        findings = compare_metadata_to_migrated_schema(database_url, settings)
    for finding in findings:
        print(f"{finding.code}: {finding.message}")
    if findings:
        print(f"Schema drift check failed with {len(findings)} finding(s).")
        return 1
    print("Schema drift check passed against an isolated migrated SQLite database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
