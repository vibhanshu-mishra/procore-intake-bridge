# Setup Experience Review

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
