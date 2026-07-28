#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.services.sandbox_smoke import (
    build_sandbox_smoke_plan,
    summarize_smoke_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a sanitized sandbox DMSA smoke plan without calling Procore."
    )
    parser.add_argument("--connection-id", type=int)
    parser.add_argument("--company-id")
    parser.add_argument("--project-id")
    args = parser.parse_args()
    settings = get_settings()
    print(
        build_sandbox_smoke_plan(
            settings,
            connection_id=args.connection_id,
            company_id=args.company_id,
            project_id=args.project_id,
        ).model_dump_json(indent=2)
    )
    print(summarize_smoke_config(settings).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
