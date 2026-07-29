# Deployment hardening (Phase A8)

A8 adds deployment profiles, sanitized readiness reports, startup checks, Alembic scaffolding,
local Docker assets, and operational guidance. It does not deploy the service or add production
authentication, cloud storage, scheduling, email, infrastructure, Procore writes, or default live
Procore reads. Passing a report is not a production security certification.

`PROCORE_INTAKE_ENVIRONMENT` accepts `local`, `staging`, or `production`. Local remains the
default. Production checks are intentionally strict and normally report blockers until an
operator supplies an external database, explicit allowed hosts, authenticated admin posture,
verified webhook posture, and external output paths. Other settings are in `.env.example`; secret
settings are references, never values.

```bash
python scripts/check_deployment_readiness.py
python scripts/check_deployment_readiness.py --strict
python scripts/check_startup_safety.py
python scripts/print_config_summary.py
```

The config summary masks database credentials. Unsafe production fails startup when configured
to fail closed; reporting blockers without raising does not approve a deployment.

Secret-provider readiness reports only adapter posture and masked required-reference status. The
local `env` provider is a strict production blocker until an approved external injection pattern
exists. `disabled`, `test`, and `external_placeholder` are also production blockers; the
placeholder makes no network call and is not a real secret-manager integration.

Migration readiness compares configured revision with repository head without running migrations.
Pending state can block strict production readiness; local defaults report a warning. Automatic
and destructive migrations remain disabled. Production execution requires a verified backup,
DBA/operator review, and recovery plan; B3 provides no production migration guarantee.

Alembic obtains its URL from runtime settings. Review revisions before `alembic upgrade head`;
never generate or run migrations against production without backups, review, and a rollback plan.

`docker compose up --build` runs local development on `127.0.0.1:8000` with a named SQLite
volume. The compose file is local-dev only and contains no production deployment guarantee.

Before launch, independently resolve every blocker; add tenant auth, TLS, rate controls,
redacted audit logs, managed database operations, tested backup/restore and incident procedures;
inject secrets externally; require signed webhooks; protect or disable admin; keep live mode
disabled until read-only scopes and allowlists are verified; and move outputs outside the repo.
Unsafe examples include SQLite in production, wildcard hosts/CORS, token-free admin, unsigned
webhooks, repository-local outputs, or unreviewed live mode.

Admin-auth readiness blocks staging/production when dashboard access is local-optional, the
primary ref/provider is unavailable, or deployment routes are unprotected. B4 header-token auth
is interim operator control, not production identity or tenant authentication.

Attachment-storage readiness validates the provider, safe-key enforcement, positive object-size
limit, health posture, fixture-download boundary, and production suitability. Local storage
remains a production blocker, test storage is forbidden outside tests, and disabled/external
placeholders fail closed. `GET /deployment/storage` is sanitized and protected with the other B4
deployment routes.
## Webhook production verification readiness

When the production receiver is enabled, signature verification is mandatory and
unverified or deprecated documentation assumptions block readiness. `needs_review` is
reported as a production warning. The verification harness itself may remain disabled;
local fixture mode does not require a report. See
[Webhook production verification](webhook-production-verification.md).
Customer-specific planning should first pass the B7 profile validator. Its blockers cover explicit
hosts, admin token references, non-SQLite production database posture, provider placeholders,
migration/recovery plans, sandbox evidence, onboarding evidence, and B6 webhook documentation.
Passing validation does not deploy or certify the application.
The B8 `GET /deployment/diagnostics` endpoint is operator-protected, read-only, no-store, and
sanitized. Support-bundle generation remains CLI-only and local; it copies no logs, database
files, attachments, payloads, environment values, or private paths.
