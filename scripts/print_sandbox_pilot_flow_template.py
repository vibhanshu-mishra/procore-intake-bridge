#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.services.sandbox_pilot_flow import build_default_flow_template


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", choices=("demo", "sandbox", "pilot"), required=True)
    args = parser.parse_args()
    print(build_default_flow_template(args.path, get_settings()).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
