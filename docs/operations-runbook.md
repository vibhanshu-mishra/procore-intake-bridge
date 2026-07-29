# Operations runbook

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
## Webhook verification and emergency stop

Run `make webhook-verification-plan` and `make webhook-docs-check` safely offline. Follow
[Webhook production verification](webhook-production-verification.md) before a deliberately
enabled synthetic run. For an emergency, disable the receiver, require signatures, rotate
the external secret, remove any external route/tunnel, inspect the queue, and purge local
verification output. B6 never creates or removes Procore hooks.
