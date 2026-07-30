# Operations runbook

For local intake visibility, use `/review`, `make review-workspace-summary`, or
`make review-workspace-check`. These H3 surfaces query the local database without mutation and
make no Procore/external call. They expose masked/hashed source context and manifest counts only,
never raw payloads, private paths, source URLs, or attachment contents.

Lifecycle operations use the guarded local workspace form/API and append an event in the same
transaction as the state update. Run `make intake-lifecycle-check` for non-writing validation and
`make intake-lifecycle-summary` for sanitized counts. Apply migration `0002_intake_lifecycle`
through the existing migration process. A local status is not a Procore status, approval,
compliance decision, or communication.

Run offline `make cloud-storage-check` before selecting a cloud provider. List, delete, and
overwrite are separate default-off gates; G2 has no presigned URLs. Readiness is not production
security approval.

Before selecting a cloud secret provider, run offline `make cloud-secret-check`. Missing optional
dependencies and configuration are reported without resource names or values. Readiness is not
production security approval.

Start with [QUICKSTART](../QUICKSTART.md). Demo is the safe default; Sandbox/Pilot require private,
operator-controlled configuration. What to run next: `make doctor`. Before committing, run
`make safety-check`.

Use the [Demo → Sandbox → Pilot order](sandbox-to-pilot-flow.md) before any separately authorized
private pilot execution.

Install with `python -m pip install -e ".[dev]"`, start with
`uvicorn app.main:app --reload`, and run tests with `pytest`. Check `GET /ready`,
`GET /deployment/readiness`, and `python scripts/check_deployment_readiness.py`. Run startup
safety with `python scripts/check_startup_safety.py`.

Run polling once with `python scripts/run_poll_once.py` and the event queue once with
`python scripts/run_event_queue_once.py`; both retain safe dry-run defaults. Inspect `/admin`
locally. Do not expose it publicly: its optional token is not production auth.

Back up the database before migrations or operational changes and test restores; copying a live
SQLite file is not a production backup strategy. Logs must never contain secrets, tokens,
Authorization headers, webhook signatures, admin tokens, App Version Keys, or private payloads.

For an incident, disable ingress, preserve sanitized evidence, rotate/revoke affected credentials
through their owner, and assign an incident owner. Detailed notification, containment, recovery,
post-incident, and access-revocation procedures remain production placeholders.

- Disable live reads: `PROCORE_INTAKE_LIVE_MODE_ENABLED=false`.
- Disable webhooks: `PROCORE_INTAKE_WEBHOOKS_ENABLED=false`.
- Disable admin: `PROCORE_INTAKE_ADMIN_DASHBOARD_ENABLED=false`.

Restart after configuration changes and inspect the sanitized readiness report.

## Secret provider audit and rotation

Run `python scripts/check_secret_provider.py` for sanitized posture and add `--strict` when
missing or unavailable refs should fail. Output contains masked names and status only; never dump
the environment to troubleshoot.

After rotating a value at its owner, update runtime injection, restart affected processes, and
repeat the audit. Revoke or rotate suspected exposure immediately. The B2 external provider is
only a fail-closed placeholder and performs no cloud or Vault request.

## Migration checks and backup

Run `python scripts/check_migration_status.py`, then exercise revisions only against temporary
SQLite with `python scripts/run_migration_safety_check.py`. Run
`python scripts/verify_schema_drift.py` before proposing schema changes.

Never run production migrations from startup. Before manual execution, verify a restorable backup,
engine compatibility, maintenance impact, revision ordering, and recovery procedure. Downgrade may
destroy data and is not a replacement for restoring a backup.

## Manual sandbox DMSA smoke

Run `python scripts/print_sandbox_smoke_plan.py` first; it never calls Procore. Follow
[`sandbox-smoke-tests.md`](sandbox-smoke-tests.md) to configure all manual gates, then invoke the
run script with an approved connection, company, project, and exact confirmation phrase. Never
use production identifiers or run it as a scheduler.

Emergency stop: set `PROCORE_INTAKE_SANDBOX_SMOKE_ENABLED=false` and
`PROCORE_INTAKE_LIVE_MODE_ENABLED=false`, restart the process, and remove the ignored
`smoke-output/` directory according to retention policy. If any credential was exposed, revoke or
rotate it immediately; do not paste it into logs or issues.

## Admin authentication and rotation

Run `python scripts/check_admin_auth.py`; use `--strict` for nonlocal review. Local can retain
`local_optional`, but staging/production needs `token_required`, a healthy primary ref, and
protected deployment routes.

During rotation, configure the previous token as the rotation ref, deploy a new primary, update
operators, then remove the overlap. Never log either value. Disable immediately with
`PROCORE_INTAKE_ADMIN_AUTH_MODE=disabled` or the dashboard-enabled switch if exposure is suspected.

## Attachment storage checks

Run `python scripts/check_attachment_storage.py` to inspect sanitized provider posture and
`python scripts/check_attachment_manifest_consistency.py` to compare downloaded local/test
manifests with object existence. Both make no external storage or Procore calls and print no
contents or private paths. Use `--strict` in reviewed gates.

Keep fixture-only downloads enabled unless a separately reviewed production adapter exists.
Missing objects require investigation and recovery from an approved source; do not bypass safe-key
validation, enable overwrite casually, expose the storage root, or construct public/presigned URLs.

For D2, run `make storage-provider-check`, `make storage-refs-check`, and the explicit temporary
write smoke test `make local-storage-provider-check`. Quality never runs the write smoke test.
Cloud posture checks make no external calls.

For D3, run `make database-check`, `make migration-plan`, and `make backup-restore-plan`. Complete
the plans privately before Pilot use. The connectivity target is separate, disabled by default,
confirmation-gated, and excluded from routine checks.

For D4, run `make deployment-check`, `make deployment-safety-check`, and
`make https-webhook-checklist`. Generate artifacts only in an ignored local or temporary output
root, then complete them through a separately authorized private deployment process.
## Webhook verification and emergency stop

Run `make webhook-verification-plan` and `make webhook-docs-check` safely offline. Follow
[Webhook production verification](webhook-production-verification.md) before a deliberately
enabled synthetic run. For an emergency, disable the receiver, require signatures, rotate
the external secret, remove any external route/tunnel, inspect the queue, and purge local
verification output. B6 never creates or removes Procore hooks.
For customer planning, run `make customer-template` and `make customer-profile-check`, resolve all
strict blockers, and generate artifacts only into ignored local output. Store any real-customer
profile and assigned contacts in an approved private system. The generated runbook is a template,
not an operational approval or deployment procedure.
For safe troubleshooting, run `make diagnostics`, generate a local bundle only when needed, and
run `make support-bundle-check` before handoff. Inspect all bundle files manually and use a private
approved channel. Never attach raw logs, a database, `.env`, payloads, screenshots, or downloaded
files.
Before any controlled pilot discussion, run `make pilot-template` and
`make pilot-readiness-check`, resolve every `NO_GO`/`BLOCKED` item, review all
`NEEDS_REVIEW` findings, and keep generated packets in ignored local output. Real approvals and
evidence belong in an approved private system.

For C1, keep actual pilot evidence outside GitHub. Print a fake template with
`python scripts/print_private_evidence_template.py`, validate a metadata-only manifest with
`python scripts/validate_private_evidence_manifest.py MANIFEST --strict`, and generate an ignored
scaffold with `python scripts/generate_private_evidence_workspace.py MANIFEST --output-root
private-evidence-output`. Confirm no workspace output is staged. The validator reads only the
manifest and makes no Procore or external calls.

For C2, run `make evidence-review-check` and `make evidence-expiry-check`. Resolve unsafe manifest
findings first, then privately address required evidence marked needs-review, expires-soon,
expired, or renewal-required. Generate review artifacts only in ignored local output, inspect
them before private handoff, and never copy a real review or signoff record into GitHub.

For C3, run `make pilot-approval-check` and `make pilot-approval-safety-check`. Resolve every
safety blocker and privately review all open readiness, expiry, renewal, launch, rollback,
limitation, risk, and signoff placeholders. Generate artifacts only in ignored local output and
never treat `ready_for_private_review` or `approved_placeholder` as real authorization.
# Mode checks

Run `make start` and `make doctor` first. Use `make try-demo` for Demo,
`make prepare-sandbox` for no-call Sandbox planning, and `make prepare-pilot` for the fake validator
chain. Sandbox smoke and all real pilot decisions remain separate, manual, private actions.

For Sandbox or Pilot preparation, run `make init-private-workspace`, privately fill only the
necessary placeholders, then run `make validate-private-workspace` and
`make private-workspace-git-safety`. Never stage the generated workspace.

Before Sandbox or Pilot authentication, run `make secret-provider-template`,
`make secret-refs-check`, and `make secret-provider-check`. Use
`make file-secret-provider-check` only for its temporary fake local self-test.
For Sandbox smoke, run the offline explain/preflight commands first. The actual live command
requires separate authorization and every manual gate. Keep sanitized output and evidence refs
private; do not register webhooks or download attachments.

For F2 use `make sandbox-read-plan`, `make sandbox-read-preflight`, and
`make sandbox-read-evidence-template` offline. The separate live command must be explicitly
authorized and exactly confirmed. It is bounded to RFI/Submittal reads, performs no writes or
webhook registration, downloads no attachments by default, and keeps sanitized results private.

For F3 run the template, check, and mapping commands against placeholder metadata only. Keep
source reports and real refs in the private evidence system; linkage neither reads them nor
approves a Pilot.

For a future public release review, run `make release-readiness` only after quality and safety
checks. Review generated drafts privately and manually. This workflow does not tag, package,
publish, or deploy.

For G3, the runtime/template/migration-plan/backup-restore-plan commands are offline. The
connectivity and migration-status targets are intentionally separate, manually gated, and
disabled by default. Never add those live targets to quality, doctor, preparation, release, or
docs checks.

G4 hosted-template commands are offline and non-deploying. Keep generated artifacts under ignored
roots or use the temporary artifact check. Never copy provider IDs, registry references, domains,
credentials, deployment logs, or real environment values into the public repository.

G5 commands are planning-only. Use temporary artifact checks or ignored roots, and keep domains,
URLs, DNS records, certificates, keys, CSRs, ACME output, secrets, webhook identifiers, reports,
and evidence outside Git. Registration and disable/rollback execution remain separate approvals.
## Hosted pilot dry run

Use G6 only to rehearse placeholder-reference coverage across plans, evidence, rollback,
monitoring, diagnostics, and support. It reads no private report contents, performs no live
operation, and grants no launch or pilot approval. Real operations remain private and manual.
## Final public readiness

H1 verifies public documentation and operational boundaries only. It performs no live operation,
reads no private report, and grants no release, production, or pilot approval. Private values and
real operations stay outside Git.
## Operator triage check

Run `make operator-triage-check` for a non-writing, empty-database-safe validation. Open
`/review/triage` for the guarded GET-only view. Treat priority as sorting only; investigate using
sanitized local detail and never copy private source data into public artifacts.

## Attachment metadata check

Run `make attachment-review-check` for a non-writing validation of local manifest metadata.
The check does not open files or contact storage. Investigate only through the sanitized
`/review/attachments` views.

## Operator export checks

Run `make operator-export-check` before generating an export. Use
`make operator-export-artifact-check` for a temporary write-and-clean exercise. Persistent local
exports use only the ignored configured root; never stage generated summaries.
