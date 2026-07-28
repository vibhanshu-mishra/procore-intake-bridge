# Project status

Current phase: A9 repository polish is complete. A1–A8 behavior and the A9 public-safety
contracts are validated by the current test suite.

B1 is implemented as a disabled-by-default, CLI-only sandbox DMSA smoke harness. Automated tests
use injected mocks; no default test calls Procore. A real run requires the explicit smoke flag,
live-mode flag, sandbox API target, exact confirmation phrase, an existing sandbox connection,
and matching allowlisted company/project identifiers.

B2 is implemented as a provider registry with local environment and in-memory test providers plus
disabled/external fail-closed placeholders. Secret references and values are separated across
DMSA, webhook, admin-token, readiness, and smoke paths. Real cloud or Vault adapters are not
implemented and remain future work.

B3 is implemented with a stable initial Alembic revision, sanitized status/readiness reporting,
and temporary-SQLite migration/drift validation. Migrations remain manual. Production still
requires DBA/operator review, verified backups, engine-specific testing, and recovery planning.

- Default runtime: local SQLite with fixture/mock intake.
- Live Procore mode: disabled by default and manually gated.
- Procore writes: none.
- Safe demo scope: synthetic connection/profile creation, fixture dry-runs, stored local mock
  events, onboarding preview, masked local admin views, and readiness reporting.
- Data safety: secret references only, no raw signed URL storage, and ignored generated outputs.

Known limitations include no production tenant authentication/authorization, managed secrets,
production database operations, cloud attachment backend, hosted scheduler, audited logging,
verified production webhook integration, or supported deployment pattern. The default readiness
report intentionally identifies production blockers. This project is not production-ready.

Passing B1 validates only a small, bounded read probe. It provides no production guarantee,
performs no attachment downloads, and persists no raw Procore payloads.

The GC/Owner must approve private DMSA installation and controls project/tool permissions.
Procore Intake Bridge is independent and is not affiliated with or endorsed by Procore.

B4 provides a secret-backed header guard for every admin and sensitive deployment route. Local
optional access remains convenient locally; nonlocal readiness requires token mode. This is not
user, tenant, role, session, OAuth, or identity-provider authentication.

B5 provides a storage-provider contract with local/test implementations and disabled/external
fail-closed placeholders. It validates object keys and adds sanitized health and manifest checks.
No production cloud adapter, public file serving, presigned URL, or live download is implemented.
