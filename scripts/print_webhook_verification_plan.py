#!/usr/bin/env python3
from app.config import get_settings
from app.services.webhook_verification import build_webhook_verification_plan


def main() -> int:
    """Print a safe plan; this function never performs network or Procore calls."""
    print(build_webhook_verification_plan(get_settings()).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
