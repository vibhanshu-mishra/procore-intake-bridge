# Database migrations

Phase B3 uses Alembic to version the SQLAlchemy schema. Stable revision
`0001_initial_schema` creates all current domain tables, constraints, and indexes without data.
SQLite is the only database exercised by B3 tests and safety scripts.

Migrations are manual. Startup does not invoke Alembic or advance `alembic_version`.
`PROCORE_INTAKE_AUTO_RUN_MIGRATIONS=false` remains the default. Readiness routes inspect revision
state only; they never upgrade or downgrade a database.

## Local checks

```bash
python scripts/check_migration_status.py
python scripts/check_migration_status.py --strict
python scripts/run_migration_safety_check.py
python scripts/verify_schema_drift.py
```

The safety check creates temporary SQLite, upgrades to head, downgrades to base, upgrades again,
validates tables, and deletes the temporary directory. Drift checking migrates a separate
temporary SQLite database and compares table/column names with SQLAlchemy metadata. Neither
contacts Procore, an external database, or a cloud service.

## Future revisions

Generate only against disposable local SQLite, then review every operation:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Normalize identifiers and names, remove unstable/environment-specific output, verify ordering and
downgrade risk, and run both safety scripts. Never accept autogenerate blindly. Table/column parity
does not prove data transformation, locking, performance, or future PostgreSQL compatibility.

## Production responsibility

Before production, an operator/DBA must review engine compatibility, locking, transformations,
capacity, and rollback limitations. Take and verify a restorable backup first. Test upgrade and
recovery against representative non-production data. A downgrade can lose data and is not a
substitute for restoring a backup.

Never put credentialed database URLs in files, command history, logs, issues, or docs. B3 masks
status URLs and refuses external-engine inspection, but provides no production migration
guarantee. Managed operations, backup automation, point-in-time recovery, online migrations, and
engine-specific validation remain future work.
A production B7 customer profile must name a non-SQLite database posture plus explicit migration,
verified backup, restore, and rollback plans. The profile validator runs no migration and connects
to no external database.
B8 diagnostics include only sanitized migration state—check enabled, at-head status, and pending
count. They include no database URL, file, schema dump, row, path, or migration execution.
B9 requires passed database/migration safety plus backup and rollback evidence. A real pilot-like
profile cannot use SQLite/local database posture; B9 runs no migration or database connection.

D3 adds `make migration-plan`, an offline execution checklist using command placeholders only.
The separately gated connectivity probe runs `SELECT 1` and never executes Alembic.

G3 adds an offline [PostgreSQL migration runbook](postgres-migration-runbook.md) and a separate,
manually gated status-only command. Neither performs upgrade or downgrade. Any future execution
requires a separate private operator decision and reviewed maintenance/rollback references.
