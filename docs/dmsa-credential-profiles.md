# DMSA credential profiles

A DMSA credential profile describes how one Bridge connection authenticates as a GC/Owner-approved
Developer Managed Service Account using OAuth client credentials. It binds an owning company,
environment, approved projects, and enabled read-only tools to opaque credential references.

## Stored and not stored

The database stores the connection name, Procore company ID, sandbox/production environment,
`dmsa_client_credentials` auth mode, `client_id_ref`, `secret_name`, permitted project IDs,
enabled tools, and connection status.

The database does **not** store plaintext client secrets, resolved client IDs, access tokens,
refresh tokens, Authorization headers, or token responses. API responses expose references but
never resolved credential values. Production should replace the local environment provider with a
managed secret service and audited access policy.

## Local environment mapping

The environment provider uppercases a reference, replaces non-alphanumeric characters with
underscores, and adds `PROCORE_INTAKE_SECRET_`.

For example:

```text
client_id_ref: demo_gc_dmsa_client_id
secret_name: demo_gc_dmsa_secret

PROCORE_INTAKE_SECRET_DEMO_GC_DMSA_CLIENT_ID=<uncommitted placeholder>
PROCORE_INTAKE_SECRET_DEMO_GC_DMSA_SECRET=<uncommitted placeholder>
```

Never place real values in `.env.example`, fixtures, tests, logs, screenshots, issues, or commits.

## Intentional live-mode opt-in

Live mode is disabled by default:

```text
PROCORE_INTAKE_LIVE_MODE_ENABLED=false
```

With the default, `mode=live` health checks resolve no credentials, build no client, and make no
network request. An approved runtime may intentionally set the flag to `true`, inject referenced
secrets, and call `POST /connections/{id}/health-check?mode=live`. This is a read-only diagnostic,
not live sync. The application currently has no tenant authentication, so exposing this route to
untrusted networks is unsafe and unsupported.

## PyProcore boundary

The adapter translates the connection and resolved references into PyProcore `ProcoreSettings`
using client-credentials auth, memory-only token storage, configured API/login URLs, and a bounded
timeout. It constructs an injected PyProcore `ProcoreClient`; no credential is copied into the
database. All live-shaped access checks stay in `app/services/procore_client.py`.

The live-gated health check performs read-only project, RFI, and Submittal collection probes for
allowlisted projects. It can show that credentials resolved, a client was constructable, and a
read endpoint responded. It cannot prove every attachment is visible, that webhook delivery works,
that permissions will remain unchanged, or that production operation is ready.

Common failures include invalid credentials, a DMSA not assigned to a permitted project, the RFIs
or Submittals tool not being enabled, attachments hidden from the DMSA, and sandbox/production URL
or credential mismatches.
