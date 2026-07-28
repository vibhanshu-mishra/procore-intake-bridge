#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.database import SessionLocal, create_db_and_tables
from app.models.connections import DMSAConnection
from app.services.sandbox_smoke import (
    MAX_SANDBOX_SMOKE_RECORDS,
    SandboxSmokeBlockedError,
    run_sandbox_dmsa_smoke,
    write_sandbox_smoke_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually run a gated, read-only sandbox DMSA smoke test."
    )
    parser.add_argument("--connection-id", type=int, required=True)
    parser.add_argument("--company-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.sandbox_smoke_enabled:
        print("Sandbox smoke blocked: the manual smoke flag is disabled.")
        return 2
    if args.max_records is not None:
        if not 1 <= args.max_records <= MAX_SANDBOX_SMOKE_RECORDS:
            print("Sandbox smoke blocked: max records must be within the safe cap.")
            return 2
        settings = settings.model_copy(
            update={"sandbox_smoke_max_records": args.max_records}
        )
    create_db_and_tables()
    with SessionLocal() as session:
        connection = session.get(DMSAConnection, args.connection_id)
        try:
            report = run_sandbox_dmsa_smoke(
                settings=settings,
                connection=connection,
                confirmation_phrase=args.confirm,
                project_id=args.project_id,
                company_id=args.company_id,
            )
        except SandboxSmokeBlockedError as exc:
            print(str(exc))
            return 2
    print(report.model_dump_json(indent=2))
    if settings.sandbox_smoke_write_report and not args.no_write_report:
        path = write_sandbox_smoke_report(
            report, settings.sandbox_smoke_output_root
        )
        print(f"Sanitized report written: {path.name}")
    return 1 if any(step.status == "failed" for step in report.steps) else 0


if __name__ == "__main__":
    raise SystemExit(main())
