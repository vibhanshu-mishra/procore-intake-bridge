# Quickstart: start with Demo Mode

J10 is a planning-only follow-up pack. Read the [post-release roadmap](docs/post-release-roadmap.md),
[known-limitations register](docs/known-limitations-register.md), [future-work backlog](docs/future-work-backlog.md),
[private-review backlog](docs/private-review-backlog.md), and [pre-tag reminder](docs/pre-tag-reminder-checklist.md)
only as inputs to a future human decision. “Post-release” means after a future human-approved
`0.1.0` release; no release happened. J10 performs no release, build, publish, upload, tag, deploy,
issue filing, ticket creation, or approval. Maintainer and private review remain required.
For local, non-writing output, run `make post-release-roadmap` and the focused targets documented
in the [command reference](docs/command-reference.md); artifact generation is temporary-only.

J8 provides a [versioned `0.1.0` release handoff](docs/versioned-release-handoff.md) for
maintainers. It is prepared metadata, not a release: no package/Docker build, publish, upload,
tag, release, docs deployment, application deployment, or workflow change occurs. Run the J8
review commands only after normal local checks; maintainer authorization and private
security/legal/infrastructure review remain required.

J7 offers `make release-candidate-review` as a non-writing checklist for prepared `0.1.0` metadata.
It does not create or approve a release candidate. No package/Docker build, publish, tag, release,
deployment, workflow automation, or approval occurs; maintainer review remains later.

J6 records `0.1.0` as prepared target/release-candidate metadata, not a released version. Use
`make version-prep-review` for the offline consistency review. It performs no build, publish, tag,
release, deployment, external registry/GitHub call, workflow change, or approval.

For a coherent documentation tour, begin with the J5 [reader paths](docs/docs-reader-paths.md).
Preview locally with `make docs-serve` only after local setup, or read the Markdown directly. J5
performs no docs deployment and adds no GitHub Pages workflow, external analytics, tracking, search,
CDN asset, or operational approval.

Phase J4 reviews existing UI surfaces for possible future hosted evaluation without deploying
anything. Run `make hosted-ui-review` for offline inspection. Demo pages use fake local SQLite data;
dashboard/admin/review pages remain protected, attachment views are metadata-only, and export packs
remain command-only. No frontend build, external asset, analytics, telemetry, public download, or
approval is added. Hosted use requires private infrastructure and security review.

Phase J3 documents all 81 local routes in the [API route reference](docs/api-route-reference.md).
Run `make api-docs-review` or `make api-route-reference` for offline inspection. Local OpenAPI is
available only after starting the local app; use fake Demo data and no external OpenAPI tooling.
These docs make no live call, add no route, and grant no production, Pilot, release, or deployment
approval. Lifecycle POST routes are local-only, webhook POST routes are signature-bound, and no
public export download, attachment file-serving, or Procore write-back route exists.

Phase J2 makes Demo Mode repeatable with deterministic fake data in local SQLite. Preview with
`make demo-seed-plan`, seed idempotently with `make demo-seed`, and verify with
`make demo-data-check`. Demo needs no Procore credentials or calls, cloud service, or external
database. `make try-demo` and `make first-run` are non-destructive. To remove only demo-marked
local records, first run `make demo-reset-plan`, then explicitly run
`make demo-reset DEMO_RESET_CONFIRMATION="RESET DEMO DATA"`. The reset never touches private
workspace, Sandbox, Pilot, Hosted, cloud, external-database, or customer data and implies no
production, Pilot, release, deployment, or Procore approval.

Phase J1's local setup order is explicit: first `python3 -m venv .venv`, second activate it with
`source .venv/bin/activate`, and third run `python -m pip install -e ".[dev]"`. Next run
`make start`, then `make try-demo`. Demo requires no Procore credentials, other secrets, cloud
services, or external database. See the [local installer guide](docs/local-installer-guide.md),
[first-run checklist](docs/first-run-checklist.md), and
[setup troubleshooting guide](docs/setup-troubleshooting-guide.md). Sandbox, Pilot, and Hosted
are separate private, gated paths. Setup performs no package or Docker build, publish, release,
or deployment and grants no production, Pilot, or release approval.

Run `make security-gap-closeout` for the offline I9 policy-versus-implementation review. It is a
guidance/checklist layer only: no scanner, external or Procore call, encryption, retention
enforcement, deletion/purge, or notification occurs. It grants no compliance, certification, or
operational approval; private security, legal, privacy, and infrastructure review remains
required.

Run `make incident-response-review` for the offline I7 boundary review.

Run `make supply-chain-review` for the offline I6 dependency and package-surface review.

Run `make infra-security-review` for the offline I5 reference, metadata, and operation-gate review. It makes no secret, storage, cloud, or database call.

For the offline Phase I4 data boundary review, run `make data-policy-review`. It reads public repository evidence only and performs no live scan or destructive deletion.

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
For a single safe local cockpit, open `/dashboard` or run:

```bash
make product-dashboard-check
make product-dashboard-overview
```

The [Product Dashboard](docs/product-dashboard.md) is read-oriented and local database only.
It makes no Procore writes or calls, offers no export downloads, and reads no attachment files.
Demo Mode may use fake local data; Sandbox and Pilot use remains private and gated.

## Evaluate the complete Demo product journey

```bash
make demo-product-check
make demo-product-tour
make demo-evaluation-checklist
```

See the [Demo Product Walkthrough](docs/demo-product-walkthrough.md). H9 uses fake data only,
makes no live or external call, and stops at the private Sandbox/Pilot boundary.

For offline security review, run `make security-threat-model` and read the
[Security Threat Model](docs/security-threat-model.md). It performs no live scan and grants no
certification or production authorization.

Run `make auth-boundary-audit` to inspect existing route and command protections offline. The
[I2 audit](docs/auth-permission-boundary-audit.md) adds no auth provider and performs no live
permission or external check.

Run `make webhook-security-review` for I3’s offline fake-fixture hardening review. It performs no
live webhook replay, webhook registration, Procore call, or external call.

## Run the final offline security review

```bash
make final-security-review
make security-readiness-summary
make security-gap-register
make private-security-review-checklist
```

I8 aggregates the I1–I7 public-repository reviews without a live scanner, external call, Procore
call, deployment, release, or build. A clear public review means ready for maintainer review only;
it grants no production, pilot, release, legal, compliance, or certification approval. Private
review of live infrastructure, credentials, customer data, legal obligations, provider
permissions, release process, incident contacts, evidence custody, and operational controls is
still required. See the [I8 guide](docs/final-security-readiness-review.md).

## J9 maintainer handoff

After the safe Demo and offline security review, use the [public maintainer handoff](docs/maintainer-handoff.md)
as the concise map of prepared `0.1.0` metadata. Run:

```bash
make maintainer-quickstart
make maintainer-review-checklist
make maintainer-command-plan
make maintainer-decision-log-template
make maintainer-handoff
```

J9 performs no release, package/Docker build, tag, publish/upload, or deployment. It makes no
external call, reads no private report, and grants no production, Pilot, release, or deployment
approval. Maintainer review and private security/legal/infrastructure review remain required.
