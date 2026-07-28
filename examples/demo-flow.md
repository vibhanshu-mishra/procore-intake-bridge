# Fixture-only demo flow

Start the app using the README quick start. These requests use fake identifiers and secret
references; they do not resolve credentials or call Procore. No credentials or live Procore
access are required.

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/safety
```

Create a synthetic local connection:

```bash
curl -s -X POST http://127.0.0.1:8000/connections \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Fake GC connection",
    "procore_company_id": "company-test",
    "environment": "sandbox",
    "permitted_project_ids": ["project-1001"],
    "enabled_tools": ["rfis", "submittals"],
    "client_id_ref": "demo/client-id-placeholder",
    "secret_name": "demo/client-secret-placeholder"
  }'
```

Assuming the returned local connection ID is `1`, create a mock sync profile and dry-run it:

```bash
curl -s -X POST http://127.0.0.1:8000/sync-profiles \
  -H 'Content-Type: application/json' \
  -d '{
    "connection_id": 1,
    "procore_project_id": "project-1001",
    "name": "Fake project fixture profile",
    "mode": "mock"
  }'

curl -s -X POST http://127.0.0.1:8000/sync-profiles/1/dry-run
curl -s -X POST 'http://127.0.0.1:8000/polling/run-once?dry_run=true'
curl -s -X POST 'http://127.0.0.1:8000/event-queue/run-once?dry_run=true'
```

Preview a non-persisted, placeholder-only onboarding packet:

```bash
curl -s -X POST http://127.0.0.1:8000/onboarding/preview \
  -H 'Content-Type: application/json' \
  -d '{
    "packet_name": "Fake onboarding preview",
    "recipient_company_name": "GC Owner Example",
    "requester_company_name": "Consultant Example",
    "app_version_key_ref": "APP_VERSION_KEY_PLACEHOLDER",
    "requested_project_ids": ["project-1001"],
    "support_contact": "SUPPORT_CONTACT_PLACEHOLDER"
  }'
```

Inspect only sanitized/local surfaces:

```bash
curl -s http://127.0.0.1:8000/admin/api/overview
curl -s http://127.0.0.1:8000/deployment/readiness
```

The local admin dashboard is at `http://127.0.0.1:8000/admin`. It is not production
authentication and must not be publicly exposed.
