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
