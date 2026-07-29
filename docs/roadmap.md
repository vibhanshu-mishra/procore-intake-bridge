# Roadmap

Completed: A1–A8 established the fixture intake service, guarded SDK boundary, polling, webhooks,
attachment manifests, onboarding, local admin, and deployment-hardening structure.

Completed: B1 adds a manually gated, mocked-by-default sandbox DMSA smoke harness.

Completed: B2 adds the secret-provider contract, masked inventory, local/test implementations,
and fail-closed external placeholders.

Completed: B3 adds deterministic initial migrations, read-only revision status, and isolated
SQLite safety/drift checks.

Completed: B4 adds secret-backed admin/deployment operator header authentication and rotation.

Completed: B5 adds the attachment storage provider contract, safe object keys, sanitized health,
local/test providers, and fail-closed external placeholders.

Possible future phases below are **not implemented or committed**:

- Future provider work: implement and review a real production secret-manager adapter.
- Future database work: production engine, online migration, backup, and recovery hardening.
- Future auth work: identity provider, users, tenants, roles, sessions, and audited access.
- D2 completed: shared local storage operations and disabled-by-default, no-call
  S3/Azure/GCS adapter boundaries with sanitized readiness.
- Future D3-D5 storage work: retention/cleanup, malware/content scanning, and
  encryption/key-management/recovery.
  controls.
- B6: webhook verification validated against current Procore documentation.
- B7: reviewed customer-specific deployment pattern.
- B8: hosted worker and scheduler.
- B9: redacted observability and audit logs.

Any future work must preserve GC/Owner control, project allowlists, read-only Procore behavior,
secret redaction, and explicit live-mode gating.
## Completed: B6 Webhook Production Verification Harness

Offline planning, manual documentation records, synthetic probes, sanitized reports, and
production readiness checks are complete. Creating, registering, changing, activating, or
deleting real Procore webhook hooks remains a future explicit write-scope phase.
Completed: B7 adds placeholder-only customer deployment profiles, offline validation, sanitized
local checklists/runbooks, and fail-closed production planning blockers.

Actual infrastructure provisioning, cloud integrations, ingress, deployment automation, private
customer configuration, and production operations remain future explicitly reviewed work.
Completed: B8 adds local operator diagnostics, strict redaction, aggregate support summaries, and
CLI-only sanitized support bundles.

Production metrics, audited structured logs, external monitoring, alerts, retention, and incident
integrations remain future separately reviewed work.
Completed: B9 adds a local controlled-pilot go/no-go profile, evidence gates, decision logic, and
sanitized readiness packet generation.

Real pilot execution, private approvals/evidence, infrastructure, launch operations, monitoring,
and production deployment remain future separately authorized work.

Completed: C1 adds placeholder-only evidence metadata schemas, fail-closed validation, and a
local ignored private-evidence workspace scaffold.

Real evidence collection, private storage integration, access audit, redaction review, retention,
reviewer handoff, and approval workflow remain future private work outside this public repository.

Completed: C2 adds placeholder review states, bounded local expiry evaluation, renewal checklists,
and sanitized ignored review artifacts.

Real reviewer authentication, private signoff records, notifications, escalation, access control,
audit history, and approval workflow remain future separately authorized private work.

Completed: C3 adds placeholder pilot approval packets, launch and rollback conditions, limitation
and risk templates, local safety validation, and ignored sanitized artifacts.

Real approval workflow, reviewer identity/access control, binding signoff, legal/compliance
review, notifications, audit history, and pilot authorization remain future private work.
# Current roadmap note

C4 (Three-Mode Quickstart and Doctor) and C5 (Private Workspace Bootstrap) are complete.
D1 (Real Secret Provider Adapters) and D2 (Real Storage Provider Adapters) are complete.
D3 (PostgreSQL and Migration Execution Readiness) is complete. D4 and D5 remain separately scoped
future work; D3 performs no automatic connection, migration, backup, or restore.
