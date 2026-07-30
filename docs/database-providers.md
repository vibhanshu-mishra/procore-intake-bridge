# Database providers

Database and cloud-storage readiness remain separate offline checks. Neither default check resolves
credentials, reads objects, or opens an external connection.

External database URL references may be resolved internally by a deliberately configured secret
provider. Default database and cloud-provider checks resolve no values or external connections.

Demo Mode uses local SQLite. Pilot expects a private PostgreSQL ref, but routine checks do not
resolve it or connect externally. What to run next: `make database-check`, then the isolated
`make migration-safety-check`.

PostgreSQL, backup, rollback, and migration planning feed
[pilot preflight](pilot-preflight.md); the flow never connects or migrates automatically.

Demo uses local SQLite and needs no external database. Sandbox may use SQLite for local simulation,
while hosted Sandbox and Pilot should use PostgreSQL through a private `DATABASE_URL` secret
reference. Database URLs, usernames, passwords, hostnames, and paths are never report fields.

Run `make database-template` and `make database-check` for offline posture checks. These commands,
doctor, diagnostics, tests, and quality never resolve the URL reference or connect externally.
Environment-backed deployments keep `DATABASE_URL` outside Git; file-provider deployments keep
the value under the ignored private secret root.

The separately gated `make database-connectivity-check` is disabled by default. It requires the
exact confirmation phrase documented in the script, resolves the URL inside the secret-provider
boundary, uses a bounded connection, and executes `SELECT 1` only. It performs no migration or
write and suppresses provider exception details.

G3 keeps SQLite as the Demo default and adds offline PostgreSQL runtime posture, connection-pool
guidance, migration planning, and recovery-drill planning for private Sandbox/Pilot use. Database
URLs remain secret-provider-managed. Live connectivity and migration-status commands are
manually gated and disabled by default.
