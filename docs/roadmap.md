# Roadmap

Completed: A1–A8 established the fixture intake service, guarded SDK boundary, polling, webhooks,
attachment manifests, onboarding, local admin, and deployment-hardening structure.

Completed: B1 adds a manually gated, mocked-by-default sandbox DMSA smoke harness.

Completed: B2 adds the secret-provider contract, masked inventory, local/test implementations,
and fail-closed external placeholders.

Completed: B3 adds deterministic initial migrations, read-only revision status, and isolated
SQLite safety/drift checks.

Possible future phases below are **not implemented or committed**:

- Future provider work: implement and review a real production secret-manager adapter.
- Future database work: production engine, online migration, backup, and recovery hardening.
- B4: authenticated and authorized admin access.
- B5: production attachment storage backend.
- B6: webhook verification validated against current Procore documentation.
- B7: reviewed customer-specific deployment pattern.
- B8: hosted worker and scheduler.
- B9: redacted observability and audit logs.

Any future work must preserve GC/Owner control, project allowlists, read-only Procore behavior,
secret redaction, and explicit live-mode gating.
