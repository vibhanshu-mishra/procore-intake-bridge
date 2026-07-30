# Project status

Phase G2 adds optional S3, Azure Blob, and GCS adapters with fail-closed gates and mocked tests.
It does not claim production security completion.

Phase G1 adds optional AWS, Azure, and GCP secret-manager adapters with fail-closed gates and
mocked tests. It does not claim production security completion.

Phase E1 audits public end-to-end usability: command discovery, first-run guidance, navigation,
troubleshooting, and safety. It adds no live integration or deployment. What to run next:
new users run `make start`; contributors run `make quality`.

Phase E2 consolidates onboarding around friendly Make targets while preserving every advanced
script and target. It adds no external integration or deployment behavior.

Phase E3 adds guided Demo, Sandbox, and Pilot tutorials, illustrative placeholder output, and an
offline walkthrough verifier. It adds no runtime feature or live action.

Phase F1 improves the existing sandbox smoke operator UX with offline preflight, explanation, and
placeholder evidence-ref tooling. It does not automate or weaken live execution gates.

Phase E4 adds advisory release-readiness checklists, sanitized local drafts, and maintainer review
guidance. No release, tag, package, image, publication, or deployment is created.

Phase E5 adds a local-only documentation-site config, journey navigation map, safety checker, and
optional preview guidance. It does not build, publish, host, deploy, or enable GitHub Pages.

Phase F2 adds separately gated bounded Sandbox RFI/Submittal list/detail validation plus offline
planning and private evidence-reference guidance. No live call runs automatically.

Phase F3 adds placeholder-only Sandbox evidence linkage into C1/C2/B9/C3/D5. It reads no private
reports, runs no validation, and grants no approval.

Phase D5, Real Sandbox-to-Pilot Flow, is implemented as a local placeholder-only workflow.
Actual private pilot execution remains future, separately authorized work.

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
fail-closed placeholders. D2 extends that boundary with safe local object operations, sanitized
readiness, private-workspace storage maps, and disabled-by-default optional cloud adapters.
No production cloud operation, public file serving, presigned URL, or live download is implemented.
D3 adds offline PostgreSQL readiness, masked database references, migration/recovery planning, and
a disabled-by-default manually confirmed `SELECT 1` connectivity boundary.
D4 is implemented as public-safe deployment recipe validation and offline HTTPS, ingress, cutover,
backup, rollback, and operator checklists. It performs no deployment or provisioning.
Phase B6, the manually gated Webhook Production Verification Harness, is implemented. It is
CLI-only, synthetic, disabled by default, documentation-aware, and makes no Procore calls.
B7 is implemented as a local-only customer deployment planning pattern with placeholder-only
profiles, fail-closed readiness validation, and sanitized ignored artifacts. It includes no
deployment automation and does not claim a production deployment or production security.
B8 is implemented with sanitized local diagnostics, aggregate database/queue summaries, protected
read-only route inventory, and a four-file local support bundle. No production observability,
telemetry, external logging, or monitoring integration is implemented.
B9 is implemented as a local-only pilot readiness gate with placeholder evidence references,
fail-closed decisions, and sanitized ignored artifacts. The fake example remains `NEEDS_REVIEW`;
no real pilot, deployment, or production security claim is made.

C1 is implemented as a CLI-only private pilot evidence workspace pattern. The public repository
contains fake manifests and validators only; generated scaffolds and all real evidence remain
private and ignored. No evidence has been collected and no pilot approval is claimed.

C2 is implemented as a CLI-only placeholder evidence review and expiry workflow with bounded
expiry windows, renewal posture, and ignored sanitized artifacts. No real reviewer, signoff,
notification, evidence review, or pilot approval is claimed.

C3 is implemented as a CLI-only placeholder pilot approval packet pattern with sanitized ignored
artifacts and a local safety checker. No real approval, identity, signoff, reviewer contact,
notification, or pilot authorization is recorded.
# Phase C4

Three-Mode Quickstart and Doctor is implemented with local-only demo, sandbox-readiness, and
pilot-readiness commands. Reports remain sanitized and generated outputs are ignored.

C5 Private Workspace Bootstrap is implemented with ignored placeholder scaffolds, strict local
validation, Git-isolation checks, and no external calls.

D1 Real Secret Provider Adapters is implemented for private environment variables and contained
local files, with disabled/fail-closed optional cloud contracts and sanitized readiness.

G3 PostgreSQL Runtime Operations Polish is implemented with optional drivers, offline pool and
runbook summaries, placeholder examples, private evidence-reference guidance, and two separate
manually gated live checks. Defaults make no external database contact, run no migration, and
inspect no backup or dump.

G4 Hosted Deployment Template Pack is implemented with nine conceptual platform profiles,
placeholder-only snippets, offline validation, temporary artifact checks, and public safety
guards. It includes no cloud calls, provisioning, image push, publication, or deployment.

G5 HTTPS/Webhook Production Setup Planning is implemented with placeholder profiles, offline
validation, ingress/TLS/DNS/disable/rollback renderers, temporary artifacts, private evidence
references, and public safety guards. It performs no public verification or registration.
