# Secret management

Phase B2 separates secret references from secret values behind a provider contract. Database
fields such as `secret_name`, `client_id_ref`, and `app_version_key_ref` store names only. Secret
values are resolved only when an explicitly gated operation needs them and never belong in
database rows, APIs, readiness output, admin pages, smoke reports, exceptions, logs, docs,
fixtures, or examples.

## Reference format

Real runtime references use the configured prefix:

```text
PROCORE_INTAKE_SECRET_DMSA_CLIENT_ID
PROCORE_INTAKE_SECRET_DMSA_CLIENT_SECRET
PROCORE_INTAKE_SECRET_WEBHOOK_HMAC
PROCORE_INTAKE_SECRET_ADMIN_TOKEN
```

`PROCORE_INTAKE_SECRET_REQUIRE_PREFIX=true` enforces that convention. Clearly fake
test/demo/placeholder refs remain accepted in tests and examples. Suspicious inline values, URLs,
bearer material, whitespace, and malformed names fail closed. Operator output masks refs,
retaining only their prefix and final characters.

## Providers

- `env` is the local-development default. It reads the variable named by the normalized ref. In
  production it requires external runtime injection and remains a strict readiness blocker until
  an approved adapter/pattern exists.
- `test` uses only a dictionary injected by unit tests and is allowed only in local mode.
- `disabled` always fails closed.
- `external_placeholder` performs no network call and reports unavailable. It is not an AWS, GCP,
  Azure, Vault, 1Password, or Doppler integration.

B2 adds no cloud SDK and no real external secret-manager adapter. Those remain future work.

## Inventory and health

```bash
python scripts/check_secret_provider.py
python scripts/check_secret_provider.py --strict
```

The CLI and `GET /deployment/secrets` report provider posture, masked required refs, and
present/missing/unknown status only. They never dump the environment or return values. DMSA
credentials, webhook HMAC material, the local admin token, and B1 smoke credentials use the same
provider contract. Health proves only reference presence, not scopes or production security.

If a credential leaks, revoke or rotate it immediately at its owner, update runtime injection,
restart affected processes, and verify sanitized health. Removing it from an issue or log is not
sufficient. Never paste leaked material into troubleshooting output.

B4 uses primary and optional rotation refs for the admin header token. Inventory and health show
only masked names/status. Both values are resolved transiently during rotation and accepted
without revealing which matched.
Customer deployment profiles contain opaque secret references only. DMSA, admin-token rotation,
webhook, and storage references must be resolved through a separately approved runtime process;
values never belong in profiles, readiness output, generated artifacts, or this repository.
Diagnostics report only secret-provider posture booleans and never reference names or values.
Support bundles reject Authorization material, token/secret assignments, database URLs, cloud
URLs, `.env` values, and absolute paths before local files are accepted.
B9 records only secret-provider posture and placeholder evidence references. It rejects secret
values and does not resolve, print, or copy any credential.

C1 evidence manifests contain opaque refs only. Never include a secret value, secret-manager
location, Authorization header, token, App Version Key, signed URL, `.env` assignment, database
URL, cloud credential, bucket URL, or storage endpoint.

C2 review manifests contain evidence refs and identity/date/signoff placeholders only. They never
contain credentials, Authorization headers, signed URLs, secret-manager locations, storage
endpoints, or real approval records.

C3 approval packets contain opaque refs and placeholders only. Credentials, Authorization
headers, signed URLs, secret-manager locations, database/storage URLs, and raw private artifacts
are prohibited.
