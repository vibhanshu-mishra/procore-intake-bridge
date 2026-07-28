#!/usr/bin/env python3
import tempfile
from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect

from app.config import get_settings
from app.database import Base
from app.services.migration_status import get_alembic_config


def main() -> int:
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="procore-migration-safety-") as directory:
        database_path = Path(directory) / "migration-safety.sqlite"
        database_url = f"sqlite:///{database_path}"
        config = get_alembic_config(settings, database_url)
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        try:
            tables = set(inspect(engine).get_table_names())
            expected = set(Base.metadata.tables) | {"alembic_version"}
            if tables != expected:
                print("Migration safety check failed: expected schema was not created.")
                return 1
        finally:
            engine.dispose()
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        print(
            "Migration safety check passed on an isolated temporary SQLite database "
            "(upgrade, downgrade, upgrade)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
