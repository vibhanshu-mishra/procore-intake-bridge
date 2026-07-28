import argparse

from app.database import SessionLocal, create_db_and_tables
from app.services.polling_worker import run_due_profiles_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Run due polling profiles once.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persist fixture intake and sync state. Default is a safe dry run.",
    )
    args = parser.parse_args()
    create_db_and_tables()
    with SessionLocal() as session:
        result = run_due_profiles_once(session, dry_run=not args.execute)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
