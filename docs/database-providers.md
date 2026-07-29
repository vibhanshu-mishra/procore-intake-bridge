# Database providers

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
