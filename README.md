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

Phase A1 deliberately uses JSON fixtures. PyProcore is installed as a dependency and has a guarded
adapter seam, but **no live PyProcore client can be created and no live Procore API is called**.

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

Connection payloads accept only a `secret_name` reference. There is no client-secret field and
Phase A1 does not resolve secret references. Dry runs never persist intake data. Runs persist only
normalized local fixture data and attachment metadata to SQLite.

## Safety model and current limitations

This service is **read-only with respect to Procore**. It has no routes or services for creating,
updating, deleting, approving, submitting, closing, or uploading Procore data. There are no
write-back routes, live API calls, external AI/model calls, MCP execution, GitHub API calls, or
automatic git/PR behavior. Tests use local fixtures only.

Phase A1 is not production-ready: health results are deterministic mocks; webhook delivery and
polling are not implemented; secret-manager integration, tenant authentication/authorization,
encryption/key management, migrations, audit logging, production databases, and live DMSA
integration remain future work. See [`docs/safety-model.md`](docs/safety-model.md).
