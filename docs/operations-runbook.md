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

## Manual sandbox DMSA smoke

Run `python scripts/print_sandbox_smoke_plan.py` first; it never calls Procore. Follow
[`sandbox-smoke-tests.md`](sandbox-smoke-tests.md) to configure all manual gates, then invoke the
run script with an approved connection, company, project, and exact confirmation phrase. Never
use production identifiers or run it as a scheduler.

Emergency stop: set `PROCORE_INTAKE_SANDBOX_SMOKE_ENABLED=false` and
`PROCORE_INTAKE_LIVE_MODE_ENABLED=false`, restart the process, and remove the ignored
`smoke-output/` directory according to retention policy. If any credential was exposed, revoke or
rotate it immediately; do not paste it into logs or issues.
