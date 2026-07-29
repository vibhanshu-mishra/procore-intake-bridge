# Pilot mode

Use [pilot preflight](pilot-preflight.md) to prepare for private review. It does not approve a
pilot, inspect real evidence, deploy infrastructure, or call external services.

Pilot mode assembles the repository's customer-profile, diagnostics, readiness, evidence review,
expiry, approval, launch-condition, and rollback tooling. Run `make pilot-check` against the
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
