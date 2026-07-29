#!/usr/bin/env python3
from app.config import Settings
from app.services.usage_modes import build_demo_mode_readiness


def main() -> int:
    readiness = build_demo_mode_readiness(Settings())
    print("Demo mode uses committed synthetic fixtures and a local SQLite database.")
    print("No Procore credentials, secrets, cloud resources, or external services are required.")
    for step in readiness.quickstart_steps:
        print(f"{step.order}. {step.title}: {step.instruction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
