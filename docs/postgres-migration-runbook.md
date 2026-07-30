# PostgreSQL migration runbook

`make postgres-migration-plan` prints an offline checklist. It does not resolve a database secret,
connect externally, or run an Alembic upgrade or downgrade.

Before a separately approved private migration:

1. Review the private maintenance-window, current-status, backup, and rollback references.
2. Confirm the responsible operator and abort criteria outside the public repository.
3. Use the manually gated status-only command if that private workflow requires it.
4. Obtain a separate execution decision; G3 provides no automatic migration runner.
5. Verify health and revision posture, then follow the private rollback plan if needed.

The status command is disabled by default and manually gated. Its public output is sanitized and
contains no revision log, SQL, URL, host, database name, username, or private path. This runbook
does not approve a production migration.
