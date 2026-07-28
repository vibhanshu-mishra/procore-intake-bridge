import argparse

from app.database import SessionLocal, create_db_and_tables
from app.services.event_queue import run_event_queue_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local event queue once.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Process queued events. Default is a safe dry run.",
    )
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    create_db_and_tables()
    with SessionLocal() as session:
        result = run_event_queue_once(
            session,
            limit=max(1, min(args.limit, 100)),
            dry_run=not args.execute,
        )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
