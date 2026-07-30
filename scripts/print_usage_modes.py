#!/usr/bin/env python3


def main() -> int:
    print("Choose a usage mode")
    print("===================")
    print(
        "READY — Demo Mode (default safe path)\n"
        "  Local synthetic fixtures; no Procore credentials or external services.\n"
        "  Best next command: make try-demo"
    )
    print(
        "\nNEEDS CONFIGURATION — Sandbox Mode (private/operator-controlled)\n"
        "  Private DMSA refs, allowed scope, and admin auth; friendly checks are offline.\n"
        "  Best next command: make prepare-sandbox"
    )
    print(
        "\nNEEDS CONFIGURATION — Pilot Mode (private/operator-controlled)\n"
        "  Private workspace, evidence, approval, database, storage, and rollback preparation.\n"
        "  Best next command: make prepare-pilot"
    )
    print("The public repository contains fake examples only; private values stay outside GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
