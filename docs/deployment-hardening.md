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
