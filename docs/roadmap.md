# Roadmap

Completed: A1–A8 established the fixture intake service, guarded SDK boundary, polling, webhooks,
attachment manifests, onboarding, local admin, and deployment-hardening structure.

Completed: B1 adds a manually gated, mocked-by-default sandbox DMSA smoke harness.

Possible future phases below are **not implemented or committed**:

- B2: production secret-manager adapter.
- B3: database migration hardening and reviewed initial schema revision.
- B4: authenticated and authorized admin access.
- B5: production attachment storage backend.
- B6: webhook verification validated against current Procore documentation.
- B7: reviewed customer-specific deployment pattern.
- B8: hosted worker and scheduler.
- B9: redacted observability and audit logs.

Any future work must preserve GC/Owner control, project allowlists, read-only Procore behavior,
secret redaction, and explicit live-mode gating.
