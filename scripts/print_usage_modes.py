#!/usr/bin/env python3


def main() -> int:
    print("Available usage modes")
    print(
        "demo    Local synthetic fixtures; no Procore credentials or external "
        "services. Run: make demo"
    )
    print("sandbox Private sandbox/DMSA configuration; readiness only. Run: make sandbox-check")
    print(
        "pilot   Private evidence, review, approval, and rollback preparation. "
        "Run: make pilot-check"
    )
    print("The public repository contains fake examples only; private values stay outside GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
