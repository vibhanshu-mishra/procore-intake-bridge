#!/usr/bin/env python3
from app.config import Settings
from app.schemas.usage_modes import UsageModeStatus
from app.services.usage_modes import build_demo_mode_readiness


def main() -> int:
    readiness = build_demo_mode_readiness(Settings())
    print(f"Demo mode: {readiness.status.value}")
    print(readiness.summary)
    for item in readiness.requirements:
        print(f"- {'ready' if item.satisfied else 'missing'}: {item.detail}")
    print("Safety: no credentials, secrets, Procore calls, or external services are used.")
    return 0 if readiness.status == UsageModeStatus.READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
