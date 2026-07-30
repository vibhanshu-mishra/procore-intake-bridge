#!/usr/bin/env python3
"""Print the conceptual G1-G5 hosted pilot dry-run reference matrix."""


def main() -> int:
    print("HOSTED PILOT OPERATIONS DRY-RUN MATRIX")
    print("Public-safe refs only; no linked contents are read and no live operation occurs.")
    rows = (
        ("G1", "Cloud secret provider plan", "SECRET_PROVIDER_PLAN_REF_PLACEHOLDER"),
        ("G2", "Cloud storage provider plan", "STORAGE_PROVIDER_PLAN_REF_PLACEHOLDER"),
        ("G3", "PostgreSQL runtime plan", "POSTGRES_RUNTIME_PLAN_REF_PLACEHOLDER"),
        ("G4", "Hosted deployment plan", "HOSTED_DEPLOYMENT_PLAN_REF_PLACEHOLDER"),
        ("G5", "HTTPS/webhook ingress plan", "HTTPS_WEBHOOK_PLAN_REF_PLACEHOLDER"),
        ("Pilot", "Evidence, readiness, approval, rollback, and operations", "REFS_ONLY"),
    )
    for phase, purpose, reference in rows:
        print(f"{phase:6} | {purpose:62} | {reference}")
    print("Human private review remains required. This is not launch or pilot approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
