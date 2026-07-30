# Migration execution plan

Run `make migration-plan` to print an offline checklist. It covers preflight review, a maintenance
window, current backup, Alembic head comparison, a manual command placeholder, verification, and
rollback. It does not execute Alembic or connect to PostgreSQL.

Real migration execution remains an operator-controlled private activity. Never commit migration
logs, database reports, SQL, dumps, credentials, or generated plans.

`make postgres-migration-plan` is the G3 PostgreSQL-specific offline checklist. It resolves no
secret, makes no external connection, and runs no migration. The live status command is separately
disabled and manually gated.
