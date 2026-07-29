# Authenticated admin access

Phase B4 adds one secret-backed header-token guard for local admin and sensitive deployment
visibility. It is not full SaaS authentication: there are no users, passwords, login pages, OAuth,
JWTs, sessions, cookies, roles, tenants, or external identity providers.

## Modes

- `local_optional` allows token-free access only when the app environment is `local`. Readiness
  blocks it for staging/production.
- `token_required` requires the configured header and primary token from the B2 SecretProvider.
- `disabled` makes admin routes unavailable with a sanitized 404.

Legacy `ADMIN_REQUIRE_TOKEN` and `ADMIN_TOKEN_SECRET_NAME` map safely for compatibility.

The default header is `X-Procore-Intake-Admin-Token`. Its value is constant-time compared with the
primary provider value. An optional rotation ref accepts the previous value during a short
operator-controlled overlap; responses never reveal which matched. Remove rotation after clients
move to the new primary.

References follow B2 masking rules. Values never appear in database rows, errors, readiness, APIs,
pages, CLI output, or logs. Provider unavailability fails closed in `token_required`.

## Routes and headers

Every `/admin` HTML and `/admin/api/*` JSON route is guarded. With deployment protection enabled,
`/deployment/readiness`, `/deployment/safety`, `/deployment/config-summary`,
`/deployment/secrets`, and `/deployment/migrations` are guarded too. `/health`, `/ready`, and
OpenAPI remain public.

Protected responses use `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, and `X-Frame-Options: DENY`.

```bash
python scripts/check_admin_auth.py
python scripts/check_admin_auth.py --strict
```

Local development can use `local_optional`. Staging/production must use `token_required`, healthy
external secret injection, protected deployment routes, and independent TLS/network controls.

For rotation, add the old value under the rotation ref, deploy a new primary, update operators,
then remove the overlap. If exposed, revoke both immediately. Disable quickly with
`PROCORE_INTAKE_ADMIN_AUTH_MODE=disabled` or the dashboard-enabled switch.

This remains interim operator-token protection. Production still needs reviewed identity-provider
integration, tenant authorization, roles, audited access, rate controls, and incident procedures.
Production customer profiles require primary and rotation admin token references. References are
configuration metadata, never token values; B7 does not implement an identity provider or claim
production-grade authentication.
