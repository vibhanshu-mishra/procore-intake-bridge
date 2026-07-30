# Quickstart

Demo Mode is the default safe path. It uses synthetic fixtures, local SQLite, and no Procore
credentials, private workspace, external database, storage setup, or deployment.

## Five-minute Demo Mode

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make first-run
make setup-demo
make demo
```

`make demo` is fixture-only. It does not call Procore or any external service. What to run next:
`make diagnostics`, or read [the complete demo walkthrough](docs/quickstart-demo.md).

## Choose your mode

### I just want to try it — Demo Mode

Use the five-minute path above. No Procore credentials are required. This is the safe default for
every new clone.

### I have Procore sandbox credentials — Sandbox Mode

First finish Demo Mode. Then read [Sandbox Mode](docs/sandbox-mode.md) and configure private DMSA
secret refs, an allowed company/project scope, and admin authentication outside Git. Run:

```bash
make sandbox-check
```

This is an offline, operator-controlled readiness check. It does not run the separately gated live
sandbox smoke harness. What to run next: follow the private checklist in the Sandbox guide.

### I want to prepare a controlled pilot — Pilot Mode

Read [Pilot Mode](docs/pilot-mode.md) and [the sandbox-to-pilot flow](docs/sandbox-to-pilot-flow.md).
Pilot Mode is private and operator-controlled. It requires an ignored private workspace, evidence
refs, review/expiry records, an approval packet, deployment and rollback planning, PostgreSQL,
secret/storage readiness, diagnostics, and a launch hold.

```bash
make init-private-workspace
make pilot-check
```

The check uses fake public examples. It does not read private evidence, approve a pilot, connect
externally, migrate a production database, or deploy.

## What must not be committed

Real credentials, IDs, names, contacts, domains, database URLs, signed URLs, evidence, approval
records, reports, logs, screenshots, attachments, certificates, backups, generated outputs, and
private workspace files must not be committed. Before committing, run:

```bash
make safety-check
```

## Common next commands

```bash
make help                    # See the small public command menu
make modes                   # Compare Demo, Sandbox, and Pilot
make doctor                  # Get readiness and the next best command
make public-usability-audit  # Check public docs, commands, files, and ignore rules
make quality                 # Run the complete local developer validation
```

## Troubleshooting with doctor

Run `make doctor`, then follow its “What to run next” guidance. It reports only sanitized posture:
no secret values, private file contents, raw environment values, or absolute paths. See
[Troubleshooting](docs/troubleshooting.md) for common setup and migration messages.

## Where files live

- Private files go in the ignored `private-workspace/` directory, or another approved private
  system outside this repository.
- Fake examples live under `examples/` and contain placeholders or synthetic data only.

Use [the command reference](docs/command-reference.md) when you need a deeper command.
