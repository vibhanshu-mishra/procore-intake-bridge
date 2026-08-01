# Safety model

I5 permits placeholder references and sanitized metadata, never secret values, database URLs, object keys, presigned URLs, contents, or live infrastructure operations.

Phase I4 maps retention and redaction boundaries offline. It excludes raw payloads, secrets, URLs, paths, storage keys, original filenames, attachment contents, and private evidence contents; it adds no destructive deletion or purge jobs.

The H3 Intake Review Workspace is GET-only and local-database-only. Its response validator blocks
raw payload keys, source URLs, signed URLs, private paths, storage keys, secrets, and raw source
IDs. Attachment bytes are never downloaded or read. Priority signals are informational and do
not create lifecycle state, approvals, compliance determinations, or Procore updates.

H4 allows only two exact, guarded lifecycle POST paths. They mutate local state and append local
audit history transactionally. The route audit rejects every other review POST and continues to
block destructive, Procore-facing, deployment, webhook-registration, and notification-style
paths. Fixed reason codes, bounded summaries, masked/hashed actors, and default-disabled free text
keep lifecycle responses public-safe. Local state is not approval or compliance state.

Cloud storage operations require independent selection, provider-enable, allow, network,
confirmation, configuration, and dependency gates. Diagnostics expose no contents, provider
resource names, object keys, credentials, signed URLs, or paths.

Cloud resolution adds independent allow, provider-enable, network, confirmation, configuration,
and dependency gates. Reports expose no values, credentials, resource identifiers, or paths.

Demo is the default safe path. Sandbox and Pilot are private/operator-controlled. Real
credentials, identities, IDs, evidence, approvals, generated/private files, and deployment
artifacts must not be committed. What to run next: `make safety-check`.

Friendly onboarding commands are local-only. `make prepare-sandbox` does not run live smoke, and
`make prepare-pilot` does not approve, connect, migrate, or deploy.

Walkthrough examples are hand-written placeholder summaries, never captured logs, screenshots,
private paths, evidence, or generated reports. `make walkthroughs-check` enforces this boundary.

F1 never invokes live smoke automatically. Its preflight resolves no credentials and makes no
external calls. The separate live runner remains sandbox-only, read-only, manually confirmed,
allowlisted, bounded, sanitized, and attachment-download-free by default.

E4 only inspects public repository posture and writes optional ignored drafts. It creates no
release, tag, package, image, publication, or deployment and never records final approval.

E5 adds navigation metadata and non-writing docs checks only. It does not build or publish a
site, enable GitHub Pages, add analytics or tracking, deploy hosting, or make MkDocs a Demo-mode
requirement. Generated site output and reports are ignored and must not be committed.

F2's plan, preflight, and evidence template are offline. Its separate live command fails closed
unless enablement, exact confirmation, Sandbox target, DMSA refs, and allowed scope pass. It reads
bounded RFIs/Submittals only, has no write/webhook/attachment methods, stores no raw payloads, and
reports only sanitized counts, statuses, and one-way hashes.

F3 consumes placeholder refs only. It blocks raw reports, records, IDs, contacts, domains, URLs,
paths, secrets, attachment data, and approval claims. It makes no Procore/external call and never
changes readiness or approval automatically.

Mode transitions are local decisions: Pilot can only become ready for private review. No
transition approves production, calls Procore automatically, or exposes private data.

Procore Intake Bridge is read-only. It performs no Procore writes: no creates, updates, deletes,
approvals, submissions, closures, uploads, or write-back routes.

Phase A2 preserves these constraints:

- Local JSON fixtures are the only sync source.
- Polling reads Procore-shaped fixture data and never writes to Procore.
- Polling dry-runs write no intake records and advance no watermarks.
- Polling tests use fixtures and mocks only.
- Webhooks never write to Procore, and the receiver does not call Procore.
- The event worker uses the existing fixture/mock read-only sync path.
- Webhook signature secrets are referenced through the secret provider, never stored.
- Webhook tests use fake payloads and fake local HMAC secrets only.
- Attachment tests perform no real downloads and use deterministic fake bytes only.
- Raw signed attachment URLs are never stored; only presence flags and hashes are retained.
- There is no attachment upload, delete, or public file-serving route.
- A5 has no S3, Azure Blob, Google Cloud Storage, presigned URLs, or cloud storage.
- Onboarding packets contain no secrets and are local Markdown/JSON artifacts only.
- Packets do not grant access; the GC/Owner controls installation, permissions, and revocation.
- A6 generates no PDF, DOCX, email, hosted link, or external delivery.
- Admin HTML and JSON routes are GET-only and read only the local database.
- Admin projections omit secret references, raw payloads, signed URLs, generated packet content,
  and absolute filesystem paths.
- The admin dashboard does not call Procore and includes no external scripts, CDNs, or analytics.
- The optional local token guard is not a substitute for production authentication, authorization,
  audited access, TLS, and network restrictions.
- No Procore endorsement, certification, partnership, affiliation, or official support is claimed.
- Live Procore access is opt-in and disabled by default.
- Live-mode adapter calls fail closed with `LiveProcoreDisabledError`.
- Mock health checks are deterministic and do not resolve credentials.
- Live-gated health checks run only after the explicit environment flag is true.
- Connection APIs accept an opaque secret reference, never a plaintext client secret.
- DMSA secrets and resolved client IDs are never stored in plaintext.
- Fixtures contain synthetic identifiers and data only.
- Tests need no credentials and make no live Procore requests.
- There are no external AI/model calls and no MCP execution.
- There are no GitHub API calls, commits, pushes, or automatic pull requests.
- `.env`, databases, tokens, downloads, and logs are gitignored.
- Production readiness is strict and does not imply production approval.
- Production must not expose the dashboard without authentication controls.
- Production webhooks must require signature verification.
- Production should not use SQLite.
- Startup checks can fail closed for unsafe production settings.
- The B1 live smoke harness is CLI-only, manual, disabled by default, and restricted to sandbox
  connections with explicit company/project allowlists and confirmation.
- B1 performs bounded read probes only: no Procore writes, raw payload persistence, raw signed URL
  reporting, attachment downloads, polling, event processing, or background execution.
- B1 automated tests use injected mocks and require no live credentials or network calls.
- Secret values resolve behind the B2 provider interface; database models retain references only.
- Provider errors, health, inventory, readiness, APIs, CLIs, admin, and smoke output never return
  secret values or raw environment dumps.
- The test provider is in-memory/local-only. Disabled and external-placeholder providers fail
  closed; B2 includes no cloud SDK or external secret-manager network call.
- B3 readiness is read-only and never upgrades or downgrades the configured database.
- Migration safety and drift scripts use disposable temporary SQLite databases only.
- Automatic and destructive migrations default off; production execution requires manual review,
  a verified backup, and an independent recovery plan.
- B4 protects all admin and sensitive deployment routes with one secret-provider-backed guard.
- Local-optional access is local-only; token/provider failures in token-required mode fail closed.
- Primary and rotation values are constant-time compared and never returned or logged.
- This header token is not full user, tenant, role, session, OAuth, or identity-provider auth.
- B5 storage accepts validated relative object keys and never stores raw signed source URLs,
  returns absolute storage paths, generates presigned URLs, or exposes public file serving.
- D2 local storage adds bounded text operations in ignored private roots. Cloud adapters remain
  disabled, make no health-check calls, and fail closed; storage D3-D5 controls remain future work.
- Database D3 treats external URLs as secret references. Routine checks never resolve them,
  connect externally, execute migrations, or inspect database dumps/backups.
- D4 deployment recipes accept placeholders only and never provision infrastructure, change DNS,
  issue certificates, register webhooks, or expose private deployment state.
- Local/test storage is bounded to development and tests. Disabled and external-placeholder
  providers make no network calls and fail closed; a production adapter remains future work.

Before production, add tenant authorization, an audited secret-manager integration, encryption and
key rotation, database migrations, data retention controls, request logging with redaction,
rate/backoff policy, and verified DMSA permission checks. Any live mode must preserve project
allowlists and expose read operations only.
## Webhook verification boundary

The B6 harness is manual, disabled by default, bounded, synthetic-only, and CLI-only. It
does not use the network, call Procore, scrape documentation, expose a route, run a worker,
or mutate webhook registrations. Reports omit raw payloads, headers, signatures, secrets,
URLs, and sensitive exception details. Current documentation must be manually verified.
B7 customer deployment profiles are local planning inputs, not deployment automation. Public
examples require fake placeholders and secret references only. Real-looking IDs, customer domains,
Authorization material, signed URLs, secret values, wildcard production hosts, and private paths
are blocked. Generated output is ignored and must not be committed.
B8 diagnostics contain posture, safe route metadata, and aggregate counts only. They exclude raw
settings/environment values, records, payloads, filenames, logs, database files, attachments,
signed URLs, local paths, contacts, and credentials. Strict redaction fails closed, support output
is ignored, and bundle generation is never exposed through an API route.
B9 accepts placeholder evidence references only. Production and real-looking identifiers are
blocked by default; private evidence, support bundles, reports, payloads, contacts, credentials,
signed URLs, and absolute paths are prohibited. A generated `GO` never means a real pilot is
approved or deployed.

C1 keeps a hard boundary between public placeholder metadata and private pilot evidence. Public
manifests cannot contain real IDs, contacts, domains, credentials, paths, URLs, raw reports,
payloads, screenshots, databases, attachments, or binary documents. Validators read only the
manifest and make no external or Procore calls; generated workspace artifacts are ignored.

C2 blocks reviewer PII, real signoffs, real IDs, contacts, domains, credentials, paths, URLs,
reports, payloads, signatures, and binary evidence. Review and expiry operate only on local
placeholder metadata, send no notifications, add no routes, and write only ignored artifacts.

C3 approval packets contain refs, statuses, counts, conditions, limitations, and signoff
placeholders only. Real approvals, identities, evidence, paths, URLs, reports, payloads,
signatures, and customer data are blocked. C3 adds no routes, notifications, or deployment.
# Three-mode boundary

Demo is fixture-only and needs no secrets or external services. Sandbox readiness inspects only
configuration posture; its live smoke mechanism stays separately gated. Pilot preparation relies
on fake public examples while all real evidence, identities, approvals, and paths stay private.
`make doctor` reports these boundaries without resolving values or making external calls.

The C5 workspace boundary is filesystem-local and ignored by Git. The public repo owns only
placeholder schemas and fake examples; privately completed refs and records remain in the ignored
workspace. Validators read safe text types under the selected root and reject unsafe content.

D1's secret boundary permits values only inside explicit provider resolution calls. Every public,
diagnostic, readiness, and doctor surface uses masked refs and booleans/counts. File resolution is
root-contained; cloud posture checks make no external calls.

G3 applies the same boundary to PostgreSQL. Offline reports contain booleans and numeric pool
settings only. Live helpers gate before secret resolution, sanitize errors, store no raw logs, and
exclude URLs, hosts, database names, usernames, query text, dump/backup material, and private
paths. No live database target participates in default automation.

G4 rejects real URLs, domains, registry/image references, secrets, certificates, cloud and
infrastructure IDs, absolute paths, logs/backups, contact details, and production-approval claims.
Generated output is ignored and contained. No GitHub Actions, Terraform, Pulumi, Kubernetes, or
Helm deployment mechanism is introduced.

G5 blocks URLs, domains, DNS records, certificate/key/CSR/ACME contents, secrets, signed URLs,
cloud credentials, database URLs, infrastructure IDs, paths, contacts, webhook payload/report
contents, webhook IDs, and completion/approval claims. All operation-attempt flags remain false.
## Hosted pilot dry-run boundary

G6 accepts placeholder refs only, reads no private report contents, and performs no live
operations. Generated output is ignored. Dry-run success is not launch or pilot approval and must
be followed by private human review.
## Final readiness boundary

H1 inspects public files and command separation only. No live operation occurs; private values and
real reports stay outside Git. A passing audit is not release, production, or pilot approval.
## H5 Operator Triage Queue

H5 reuses H3 sanitization and reads H4 state without creating or changing it. Responses exclude
raw payloads, source and signed URLs, private paths, attachment contents, and raw source IDs.
Unsafe exposure configuration fails closed. The queue makes no assignment, comment, approval,
compliance decision, communication, notification, lifecycle transition, or Procore update.

## H6 Attachment Review

H6 reads only local database manifest metadata. It never opens or serves a file, contacts a
storage provider, or downloads a Procore attachment. Responses exclude URLs, private paths,
storage keys, original filenames, checksum values, raw identifiers, payloads, and contents.
Unsafe exposure settings fail closed.

## H7 Operator Export Pack

H7 has no web route. Its read-only builders reuse sanitized H3–H6 projections; only the explicit
CLI generator writes to allowlisted ignored or `/tmp` roots. Output excludes private values and
neutralizes spreadsheet formula prefixes. Traversal and unsafe exposure configuration fail
closed. Export summaries are not approvals, compliance reports, customer reports, certifications,
or Procore statuses.
# Product dashboard boundary

H8 is aggregate, local, and read-oriented. Raw payloads, URLs, private paths, storage keys,
filenames, contents, secrets, and raw source identifiers are blocked. Dashboard readiness is not
release, production, or pilot authorization and is not a compliance determination or customer
report.

H9 reads public repository guidance and route metadata only. It makes no live call, database
write, deployment, release, or private report read. Optional outputs are ignored and
fail-closed; Demo completion grants no external authorization or certification.

I1 formalizes these controls in an [offline threat model](security-threat-model.md). Passing it
does not establish production security, certification, compliance, launch, or Pilot authorization.

I2 adds an [offline auth/permission boundary audit](auth-permission-boundary-audit.md). It checks
existing admin guards, webhook signature boundaries, local mutations, public status routes, and
manual CLI gates without adding an auth provider or performing a live permission check.

I3 adds an [offline webhook hardening review](webhook-replay-signature-hardening.md) for HMAC,
exact request bytes, constant-time comparison, deduplication, local replay, redaction, and fake
fixtures. It performs no live replay or registration.
