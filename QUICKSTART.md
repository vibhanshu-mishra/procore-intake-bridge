# Quickstart: start with Demo Mode

For private Sandbox or Pilot storage, start local. Optional cloud storage is disabled and offline
by default; see [docs/cloud-storage-providers.md](docs/cloud-storage-providers.md).

For private Sandbox or Pilot configuration, start with `env` or `file`. Optional cloud secret
providers are disabled and offline by default; see
[docs/cloud-secret-providers.md](docs/cloud-secret-providers.md).

Demo Mode is the default safe path. It uses synthetic fixtures, local SQLite, and no Procore
credentials, private workspace, external database, storage setup, or deployment.

## Five-minute Demo Mode

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make start
make try-demo
```

`make try-demo` is fixture-only. It does not call Procore or any external service. What to run next:
read the [guided Demo walkthrough](docs/walkthrough-demo.md), then use the
[walkthrough index](docs/walkthrough-index.md) for optional private paths.

## Choose your mode

### I just want to try it — Demo Mode

Use the five-minute path above. No Procore credentials are required. This is the safe default.

### I have Procore sandbox credentials — Sandbox Mode

First finish Demo Mode. Then read [Sandbox Mode](docs/sandbox-mode.md) and configure private DMSA
secret refs, an allowed company/project scope, and admin authentication outside Git. Run:

```bash
make prepare-sandbox
```

This is an offline, operator-controlled readiness check. It does not run the separately gated live
sandbox smoke harness. What to run next: follow the private checklist in the Sandbox guide.
Use `make sandbox-smoke-explain` and `make sandbox-smoke-preflight` for offline guidance; neither
command calls Procore.
F2 planning is also offline: use `make sandbox-read-plan` and `make sandbox-read-preflight`.
The live `make sandbox-read-validation` command is never a quickstart/default step.
Later, `make sandbox-evidence-check` validates fake opaque-reference linkage only. It reads no
private reports and does not approve a Pilot.

### I want to prepare a controlled pilot — Pilot Mode

Read [Pilot Mode](docs/pilot-mode.md) and [the sandbox-to-pilot flow](docs/sandbox-to-pilot-flow.md).
Pilot Mode is private and operator-controlled. It requires an ignored private workspace, evidence
refs, review/expiry records, an approval packet, deployment and rollback planning, PostgreSQL,
secret/storage readiness, diagnostics, and a launch hold.

```bash
make prepare-pilot
make init-private-workspace
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
make commands                # See grouped friendly and advanced commands
make next                    # Get the best next command
make doctor                  # Get readiness and the next best command
make try-demo                # Run the safe fixture demo
make prepare-sandbox         # Run offline Sandbox preparation
make prepare-pilot           # Run offline Pilot preparation
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
For a command-by-command journey, continue to the
[guided walkthroughs](docs/walkthrough-index.md).
The optional [documentation-site guide](docs/docs-site.md) and
[navigation map](docs/docs-navigation.md) provide local-only navigation; MkDocs is not required
for Demo Mode and the repository publishes no docs site.
Maintainers can later consult [release readiness](docs/release-readiness.md); this is never part
of first-run Demo, Sandbox, or Pilot execution.

PostgreSQL is optional for private Sandbox/Pilot hosting; SQLite remains the Demo default.
`make postgres-runtime-check` is offline. Live database checks are separate, manually gated, and
disabled by default; planning commands run no migration and inspect no backup or dump.

Hosted platform templates are optional conceptual aids for private Sandbox/Pilot preparation.
They are placeholder-only, are not deployment automation, make no cloud calls, and do not replace
private HTTPS, provider, production, or release review.

HTTPS webhook planning is optional and offline. The local expected receiver path does not prove
public reachability. Real HTTPS, ingress, DNS/TLS, signature secrets, registration, evidence, and
production review remain private and manual.

The hosted pilot dry run combines G1–G5 and pilot-workflow placeholder references without reading
linked report contents. Run `make hosted-pilot-dry-run-check` or
`make hosted-pilot-dry-run-matrix`; neither performs a live operation. The result is not a launch
or pilot approval and requires private human review.

Maintainers can run `make final-readiness` after `make quality`, `make safety-check`,
`make docs-site-check`, and `make release-readiness`. H1 performs no live operation and is not
release, production, or pilot approval. Private values and real reports stay outside Git.

## Review fake intake records

After `make try-demo`, open `/review` or run `make review-workspace-summary`. The Demo command
remains a safe dry run, so an empty workspace is expected until fake fixture persistence is
explicitly requested. The
[Intake Review Workspace](docs/intake-review-workspace.md) reads only the local database. It makes
no Procore call or write, exposes no raw payload or attachment content, and adds no lifecycle
transition.

H4 enables audited local status changes from the record detail page. Run
`make intake-lifecycle-check` or read the
[lifecycle guide](docs/intake-lifecycle-status-flow.md). A local status does not update Procore
and is not an approval, compliance determination, assignment, or communication.
## Inspect the local triage queue

After the Demo flow, open `/review/triage` or run:

```bash
make operator-triage-check
make operator-triage-summary
```

These H5 commands only read sanitized local H3/H4 data. Priority is a sorting helper, and no
Procore write, lifecycle transition, assignment, comment, approval, notification, or external
call occurs. See [Operator Triage Queue](docs/operator-triage-queue.md).

## Review attachment manifest metadata

After local Demo ingestion, open `/review/attachments` or run:

```bash
make attachment-review-check
make attachment-review-summary
```

H6 reads local manifest metadata only. No attachment file, private path, storage key, filename,
URL, or content is exposed or accessed.

## Preview sanitized export summaries

```bash
make operator-export-check
make operator-export-summary
```

These H7 commands write nothing. Local artifact generation is a separate explicit command and
its output remains ignored. Exports are metadata summaries, not customer or compliance reports.
