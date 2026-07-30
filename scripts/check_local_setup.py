#!/usr/bin/env python3
from app.config import Settings
from app.schemas.usage_modes import UsageModeStatus
from app.services.usage_modes import build_demo_mode_readiness


def main() -> int:
    readiness = build_demo_mode_readiness(Settings())
    print("Demo Mode local check")
    print("=====================")
    print(f"Status: {readiness.status.value}")
    print(readiness.summary)
    missing = [item.detail for item in readiness.requirements if not item.satisfied]
    if missing:
        print("Needs attention:")
        for detail in missing:
            print(f"- {detail}")
    else:
        print("All required local checks passed.")
    print("Safe by default: no credentials, Procore calls, or external services.")
    print("Best next command: make try-demo")
    return 0 if readiness.status == UsageModeStatus.READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
