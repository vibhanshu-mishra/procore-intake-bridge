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
- `GET`, `POST`, and `PATCH /sync-profiles`
- `POST /sync-profiles/{id}/dry-run`
- `POST /sync-profiles/{id}/run-once`
- `GET /sync-profiles/{id}/state`
- `POST /polling/run-once` (safe default: `dry_run=true`)
- `POST /webhooks/procore` and `POST /webhooks/procore/dry-run`
- `GET /webhook-events` and `GET /webhook-events/{id}`
- `POST /webhook-events/{id}/replay`
- `POST /event-queue/run-once` (safe default: `dry_run=true`)
- `GET /attachments` and `GET /attachments/{id}`
- `POST /attachments/plan`
- `POST /attachments/{id}/fixture-download`
- `GET /intake-records/{id}/attachments`
- `GET /onboarding/default-permissions`
- `POST /onboarding/preview` and `POST /onboarding/generate`
- `POST /connections/{id}/onboarding-packet`
- `POST /onboarding-packets/{id}/export-local`
- `GET /admin` and the read-only pages beneath `/admin/*`
- `GET /admin/api/overview`, `/admin/api/safety`, and read-only list APIs beneath `/admin/api/*`

Connection payloads accept `client_id_ref` and `secret_name` references. There is no client-secret
field. Environment-backed resolution is available only to the live-gated health path. Dry runs
never persist intake data. Runs persist only normalized local fixture data and attachment metadata
to SQLite; Phase A2 does not add live sync.

Health checks default to `mode=mock`. `mode=live` returns a safe disabled result unless
`PROCORE_INTAKE_LIVE_MODE_ENABLED=true`. See
[`docs/dmsa-credential-profiles.md`](docs/dmsa-credential-profiles.md) for the intentional opt-in
and environment-variable mapping.

Phase A3 adds project-level polling profiles, watermarks, retry state, and overlap protection. It
is intentionally a run-once worker rather than a daemon or scheduler. The polling endpoint and
[`scripts/run_poll_once.py`](scripts/run_poll_once.py) default to dry-run; pass
`?dry_run=false` or `--execute` only to persist fixture intake and local sync state. See
[`docs/polling-worker.md`](docs/polling-worker.md).

Phase A4 adds a store-first webhook receiver and local database event queue. The receiver verifies
or safely skips a configurable HMAC signature, redacts sensitive payload keys, normalizes and
deduplicates the event, and stores it without calling Procore or running sync. The event worker
later maps queued RFI/Submittal events to mock `SyncProfile`s. Try
`POST /webhooks/procore/dry-run` to inspect normalization without persistence and
`POST /event-queue/run-once?dry_run=true` to preview queued processing. See
[`docs/webhooks.md`](docs/webhooks.md).

Phase A5 adds local attachment manifests and a filesystem storage abstraction. Intake sync plans
safe relative keys, sanitizes filenames, and stores only whether a source URL existed plus its
SHA-256 hash—never the URL. No real attachment download is available. The explicitly named
fixture-download route writes a small deterministic local file for testing only, with overwrite
disabled by default. See [`docs/attachment-storage.md`](docs/attachment-storage.md).

Phase A6 adds an offline GC/Owner onboarding packet generator. It renders professional Markdown
and JSON covering DMSA/private-app purpose, requested projects, minimum permissions, data access,
safety boundaries, installation review, health checks, troubleshooting, control/revocation, and
the independent-tool disclaimer. Preview does not persist; generate stores a review copy locally;
export writes only Markdown/JSON beneath a gitignored directory. No email, PDF, DOCX, hosted link,
installation, or Procore call is performed. See
[`docs/onboarding-packets.md`](docs/onboarding-packets.md).

Phase A7 adds a minimal local admin dashboard over the existing database. Every admin route is
GET-only and uses dedicated masked/redacted projections; it does not expose credential references,
raw webhook or intake payloads, signed URLs, generated onboarding content, or absolute storage
paths. It makes no Procore calls. The default token-free configuration is only for local
development and is not production authentication. See
[`docs/admin-dashboard.md`](docs/admin-dashboard.md).

## Safety model and current limitations

This service is **read-only with respect to Procore**. It has no routes or services for creating,
updating, deleting, approving, submitting, closing, or uploading Procore data. There are no
write-back routes, external AI/model calls, MCP execution, GitHub API calls, or automatic git/PR
behavior. Live read checks are opt-in; tests use local fixtures and mocks only and never use the
network.

The service is not production-ready: the environment secret provider and admin dashboard are for
controlled local development; hosted scheduling and webhook delivery infrastructure are not
implemented; managed secret storage, tenant authentication/authorization, migrations, audit
logging, and production databases remain future work. See
[`docs/safety-model.md`](docs/safety-model.md).
