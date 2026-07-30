# PostgreSQL runtime operations

Phase G3 extends the D3 readiness posture and D4 deployment planning with private,
operator-controlled runtime guidance. SQLite remains the Demo default. PostgreSQL is intended for
Sandbox, Pilot, or privately hosted operation.

`make postgres-runtime-check` is offline: it does not resolve the database URL reference, connect
to an external database, run a query, migrate a schema, inspect a backup, or restore data. The URL
must remain managed by the selected private secret provider.

The connectivity and migration-status commands are separate live commands. They are disabled by
default and manually gated by the provider selection, master runtime switch, operation switch,
exact confirmation, safe masking policy, and private database reference. Neither belongs to
quality, doctor, preparation, release, or documentation checks. Connectivity is a bounded,
read-only probe; migration status never upgrades or downgrades.

Offline reports contain settings posture and numeric pool guidance only. They exclude database
URLs, hosts, database names, usernames, credentials, query text, raw logs, backup or dump names
and contents, and private paths. They do not imply approval of a production database operation or
a Pilot.

Start with:

```bash
make postgres-runtime-template
make postgres-runtime-check
make postgres-migration-plan
make postgres-backup-restore-plan
```

Keep maintenance-window, backup, restore-drill, rollback, and migration-status evidence references
in the private workspace.
## G6 handoff

G6 links a placeholder PostgreSQL runtime plan reference without connecting, migrating, backing
up, restoring, or reading reports. The dry run is not launch or pilot approval.
