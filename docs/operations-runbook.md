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
