# Setup Experience Review

## J2 relationship

J2 extends local setup with deterministic fake Demo Mode seed, inventory, and reset planning for
local SQLite only. It makes no Procore, cloud, or external-database call. `make try-demo` and
`make first-run` remain non-destructive; the sole reset command requires the exact confirmation
and affects only demo-marked records. Private workspace, Sandbox, Pilot, Hosted, cloud, and
customer data are outside its boundary. No production, Pilot, or release approval is implied.

Phase J1 is an offline, local-only maintainer review of prerequisites, setup documentation,
commands, mode boundaries, ignored generated outputs, and troubleshooting guidance. It reads
curated public repository files only.

Run the non-writing review commands:

```bash
make setup-experience-review
make first-run-checklist
make local-installer-guide
make setup-troubleshooting-guide
```

Artifact generation is separate and explicit through `make setup-experience-artifact-check`.
Generated reports, checklists, guides, command maps, and manifests stay in ignored output paths
and must contain only sanitized public-safe content.

## Review contract

The review verifies Git, Python 3.12+, pip, Make, virtual-environment, local dependency-install,
Demo, safety-check, docs, and next-command guidance. It expects Demo Mode to require no Procore
credentials and no secrets, cloud services, or external database. Sandbox, Pilot, and Hosted are
separate private, manually gated paths.

The reviewer performs no dependency installation, Procore or external call, database connection
or write, cloud access, scanner call, package or Docker build, publish, tag, release, deployment,
workflow change, or private-report read. There is no deploy and no release operation. It grants
no production approval, Pilot approval, release approval, deployment approval,
security, certification, compliance, legal, or Procore approval.

Start with the [local installer guide](local-installer-guide.md), follow the
[first-run checklist](first-run-checklist.md), and use the
[setup troubleshooting guide](setup-troubleshooting-guide.md) if a prerequisite is missing.
