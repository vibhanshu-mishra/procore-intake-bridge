# Troubleshooting

Start with `make doctor`. It is local-only and prints sanitized readiness plus what to run next.

## Repository or workspace path is wrong

Run commands from the repository root—the directory containing `Makefile`, `app/`, and `scripts/`.
Do not paste an absolute workstation path into public docs, reports, or issues.

## Virtual environment or dependencies are missing

Create `.venv`, activate it, and install `python -m pip install -e ".[dev]"`. If `SQLAlchemy`,
FastAPI, or another import fails, the editable install is missing or the wrong Python is active.
Run `python -m pip check`, then `make doctor`.

## SQLite reports a pending migration

Local migration status may show the initial migration as pending depending on the state of the
local SQLite database. That is not permission to mutate an external database. The safer public
validation is `make migration-safety-check` and `make schema-drift-check`, which use isolated
temporary SQLite databases.

## Starlette/httpx warning

The existing Starlette/httpx deprecation warning is known and non-blocking. Treat a test failure
as actionable; the warning alone does not mean Demo Mode failed.

## Generated output is ignored by Git

That is intentional. Demo, sandbox, pilot, support, evidence, first-run, usability, and private
workspace outputs must stay untracked. Use `git status --short` and `make safety-check`; do not
force-add ignored output.

## Private workspace is not found

Demo Mode needs no private workspace. For private Sandbox or Pilot preparation, run
`make init-private-workspace`, complete files privately, and validate with
`make private-workspace-check`.

## Secret refs are missing

Sandbox requires private DMSA refs; Pilot requires private secret-provider readiness. Put values
only in the approved private provider. Public configuration stores refs, never secret values. See
[Secret providers](secret-providers.md).

## Storage root is missing

Demo does not need storage setup. For local private storage, configure a contained ignored root and
run `make storage-provider-check`. Cloud adapters are fail-closed unless privately implemented and
reviewed.

## PostgreSQL is not configured

Demo uses SQLite. Pilot readiness expects a private PostgreSQL reference and operator-reviewed
migration, backup, and rollback plans. Routine public checks do not resolve the reference or
connect externally. See [Database providers](database-providers.md).

## Sandbox smoke is not ready

`make sandbox-check` intentionally checks only offline onboarding posture and does not run live
smoke. A live sandbox probe remains separately gated, manually confirmed, allowlisted, read-only,
and operator-controlled. Never use public example IDs or credentials for a real run.

## Pilot preflight is not ready

`make pilot-check` uses fake examples and must not approve a pilot or read private evidence.
Resolve private readiness in the ignored workspace, keep launch on hold, and follow
[Pilot Mode](pilot-mode.md). A passing public check is not production approval.
