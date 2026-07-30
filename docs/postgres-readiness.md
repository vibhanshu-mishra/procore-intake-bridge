# PostgreSQL readiness

Pilot posture requires PostgreSQL when `PROCORE_INTAKE_POSTGRES_REQUIRED_FOR_PILOT=true`. Readiness
requires a valid private URL reference, SSL policy, migration planning, and backup/rollback
planning. The minimum configured major version is 14, but no server version or permission is
probed automatically.

Readiness reports contain provider, mode, booleans, findings, and next steps only. A ready report
is configuration posture—not proof of connectivity, backup recovery, security, or deployment.

Continue with [runtime operations](postgres-runtime-operations.md). G3 builds on this D3 readiness
report without changing its no-connect default; pool settings are guidance, migration plans
execute nothing, and backup/restore plans inspect no files.
