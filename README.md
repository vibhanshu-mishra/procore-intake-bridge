# Procore Intake Bridge

Procore Intake Bridge is a private, read-only backend intake service for subcontractors,
consultants, and engineering firms. It pulls RFIs, Submittals, and attachments visible through
those items from GC/Owner-owned Procore projects into the customer's own tracking system.

## Why DMSA

A Developer Managed Service Account (DMSA) lets a GC or Owner install a private app, associate a
dedicated service identity, and limit that identity to approved projects and read-only tools. This
avoids depending on an employee's account and makes access intentional and auditable.

## Architecture

[PyProcore](https://pypi.org/project/pyprocore/) is the SDK layer responsible for Procore
authentication, requests, pagination, typed parsing, retries, and download plumbing. This app is
the product layer: connection profiles, project allowlists, sync state, normalized intake records,
attachment manifests, logs, health checks, onboarding, and future polling/webhook coordination.

Fixture sync still deliberately uses local JSON. Phase A2 adds a production-shaped DMSA credential
profile and an injected PyProcore client boundary. **Live mode is disabled by default** and must be
explicitly enabled before the adapter can resolve credentials or construct a live client.
Therefore, no live Procore calls occur during normal local development or tests.

## Local setup

Python 3.12 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

SQLite is the default local database. Copy `.env.example` to `.env` only to customize safe local
settings. Never place credentials, tokens, real company/project IDs, or client data in committed
files.

## Routes

- `GET /health`, `GET /ready`, and `GET /safety`
- `GET /connections`, `POST /connections`, and `GET /connections/{id}`
- `POST /connections/{id}/health-check`
- `POST /connections/{id}/sync/dry-run`
- `POST /connections/{id}/sync/run`

Connection payloads accept `client_id_ref` and `secret_name` references. There is no client-secret
field. Environment-backed resolution is available only to the live-gated health path. Dry runs
never persist intake data. Runs persist only normalized local fixture data and attachment metadata
to SQLite; Phase A2 does not add live sync.

Health checks default to `mode=mock`. `mode=live` returns a safe disabled result unless
`PROCORE_INTAKE_LIVE_MODE_ENABLED=true`. See
[`docs/dmsa-credential-profiles.md`](docs/dmsa-credential-profiles.md) for the intentional opt-in
and environment-variable mapping.

## Safety model and current limitations

This service is **read-only with respect to Procore**. It has no routes or services for creating,
updating, deleting, approving, submitting, closing, or uploading Procore data. There are no
write-back routes, external AI/model calls, MCP execution, GitHub API calls, or automatic git/PR
behavior. Live read checks are opt-in; tests use local fixtures and mocks only and never use the
network.

Phase A2 is not production-ready: the environment secret provider is for controlled local
development; webhook delivery and polling are not implemented; managed secret storage, tenant
authentication/authorization, migrations, audit logging, and production databases remain future
work. See [`docs/safety-model.md`](docs/safety-model.md).
