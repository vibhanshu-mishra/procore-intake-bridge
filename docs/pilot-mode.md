# Pilot mode

The H3 Intake Review Workspace is read-only and does not approve a Pilot. Pilot records,
identifiers, and evidence remain private and gated; raw payloads and attachment contents are not
exposed. No assignment, comment, approval, lifecycle transition, or Procore write is available.

Pilot storage selection is a private operator decision. Cloud storage readiness does not approve
production security or a pilot, and default preflight checks perform no cloud object operations.

Pilot provider selection is a private operator decision. Optional cloud readiness does not approve
production security or a pilot, and default preflight checks do not contact cloud services.

Pilot Mode is private and operator-controlled. It requires a private workspace, evidence refs,
review/expiry records, approval, deployment/rollback planning, and database, secret, storage, and
diagnostic readiness. What to run next: `make prepare-pilot`, then `make init-private-workspace`
only when authorized. Keep launch on hold.

Follow the [Pilot walkthrough](walkthrough-pilot.md) for the ordered private preparation and
required human review.

Use [pilot preflight](pilot-preflight.md) to prepare for private review. It does not approve a
pilot, inspect real evidence, deploy infrastructure, or call external services.

Pilot mode assembles the repository's customer-profile, diagnostics, readiness, evidence review,
expiry, approval, launch-condition, and rollback tooling. Run `make prepare-pilot` against the
committed fake examples and `make doctor` for a concise posture summary.

Real evidence, identities, signoffs, decisions, customer identifiers, and credentials belong in an
authorized ignored private workspace outside GitHub. The public repository never supplies or
records a real approval. Pilot mode remains `needs_configuration` until operators complete that
private work; its validators do not constitute production approval or security certification.

Use `python scripts/init_private_workspace.py --mode pilot` for the C5 ignored scaffold covering
customer profile, evidence refs, review/expiry, readiness, approval, launch, rollback, and incident
response. Real evidence, signoffs, identities, and decisions remain outside GitHub.

A real pilot must select `env`, `file`, or a separately verified optional cloud provider.
`external_placeholder`, `test`, and `disabled` remain fail-closed and do not establish pilot
secret-management readiness.

D3 Pilot posture requires PostgreSQL by default, with SSL, migration execution, backup, restore,
and rollback plans completed privately. Readiness does not connect or run migrations.

Pilot should also complete a private D4 deployment recipe, cutover checklist, HTTPS/ingress review,
backup/rollback runbooks, and operator runbook. These artifacts are not deployment automation.

For a private PostgreSQL Pilot, review the G3 runtime posture and pool guidance. The default
commands do not connect externally. Live connectivity and migration-status checks remain separate,
manually gated steps and do not approve the Pilot or a production database.

Hosted platform profiles are planning aids only. A Pilot still requires private provider values,
HTTPS and ingress setup, database/storage/secret configuration, recovery evidence, production
review, and a separate manual deployment decision.

A Pilot that plans real webhooks requires privately reviewed HTTPS/public ingress, DNS/TLS,
signature-secret, queue/replay, monitoring, disable, rollback, and evidence references. G5 never
registers a webhook and never grants Pilot approval.
## Hosted operations rehearsal

The G6 hosted pilot dry run maps opaque G1–G5, evidence, readiness, rollback, and operations
references without reading private report contents or performing live operations. It is not a
launch or pilot approval. Keep real work private/manual and require human review.
## H1 boundary

Final public readiness happens before private Pilot work. It performs no live operation and grants
no release, production, or pilot approval. Private values and real reports stay outside Git.
