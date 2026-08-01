# Documentation

## Start here

Choose a canonical [reader path](docs-reader-paths.md), use the
[navigation map](docs-navigation-map.md) for topic grouping, and keep the
[command reference](command-reference.md) as the single source for executable commands.

- **First-time evaluator:** local setup → fake Demo seed → product walkthrough → API reference.
- **Demo user:** review workspace → lifecycle → triage → attachment metadata.
- **Sandbox/Pilot preparer:** private, manually gated mode guidance.
- **Hosted preparer:** hosted UI planning → private infrastructure/security gates.
- **Security or release reviewer:** threat/security closeout → readiness and release review.

Phase J5 polishes local navigation only. The site may be previewed locally with `make docs-serve`;
no docs deployment, GitHub Pages workflow, external analytics, tracking, search service, or CDN
asset is added. Documentation grants no production, Pilot, release, deployment, or hosting approval.

Phase J4 provides [hosted UI preparation](hosted-ui-preparation.md), a
[page inventory](hosted-ui-page-inventory.md), [readiness checklist](hosted-ui-readiness-checklist.md),
and [private gates](hosted-ui-private-gates.md). The review is offline and non-deploying. It adds no
frontend build, external assets, analytics, or telemetry; protected pages stay protected,
attachments stay metadata-only, and exports remain command-only. Hosted evaluation still requires
private infrastructure/security review and receives no operational approval from J4.

Phase J3 provides an offline [API documentation review](api-docs-review.md), an all-81-route
[reference](api-route-reference.md), [Demo-safe examples](api-usage-examples.md), and a
[local OpenAPI guide](openapi-local-guide.md). It adds no product behavior, makes no live call,
and uses no external OpenAPI tooling. Lifecycle mutations remain local-only, webhook POST routes
remain signature-bound, protected surfaces stay protected, and no export download, file-serving,
or Procore write-back route is introduced. Documentation grants no operational approval.

Phase J2 provides [local Demo data seed/reset guidance](demo-data-seed-reset.md), a
[non-destructive seed plan](demo-seed-plan.md), and a [fail-closed reset guide](demo-reset-guide.md).
The experience uses deterministic fake data in local SQLite only, with no Procore call, cloud
service, external database, private workspace, or customer data. `make try-demo` is
non-destructive; only `make demo-reset` can remove demo-marked records and it requires the exact
confirmation phrase. No production, Pilot, or release approval is implied.

Phase J1 provides a [local installer guide](local-installer-guide.md), canonical
[first-run checklist](first-run-checklist.md), [setup troubleshooting](setup-troubleshooting-guide.md),
and an offline [setup experience review](setup-experience-review.md). First create `.venv`, second
activate it, and third install local development dependencies; then run `make start` and
`make try-demo`. Demo needs no credentials, cloud service, or external database. Sandbox, Pilot,
and Hosted are separate gated paths. Setup builds, publishes, releases, and deploys nothing and
grants no operational approval.

Phase I9 provides an [offline security gap closeout](security-gap-closeout.md) that distinguishes
implemented behavior from policy, guidance, intentional omissions, private review, and future
work. Its privacy template and encryption-at-rest guidance are review aids only. I9 performs no
live scan, external or Procore call, encryption, retention enforcement, deletion/purge, or
notification and grants no compliance, certification, or operational approval.

See the [I7 incident-response/forensics readiness review](incident-response-forensics.md).

See the [I8 Final Security Readiness Review](final-security-readiness-review.md),
[security readiness summary](security-readiness-summary.md),
[security gap register](security-gap-register.md), and
[private security review checklist](private-security-review-checklist.md). I8 aggregates I1–I7
offline and grants no production, pilot, release, legal, compliance, or certification approval.

See the [I6 dependency and supply-chain security review](dependency-supply-chain-security.md).

See the [I5 secrets/storage/database security review](secrets-storage-db-security-review.md) for offline provider and operation boundaries.

Security review continues with the [Phase I4 Data Retention and Redaction Policy](data-retention-redaction-policy.md), an offline, non-destructive public repository check.

Follow this beginner order: [Quickstart](../QUICKSTART.md), [usage modes](usage-modes.md),
[command reference](command-reference.md), [Demo walkthrough](quickstart-demo.md), then
[Sandbox](sandbox-mode.md) or [Pilot](pilot-mode.md). Start with `make start`.

For the complete guided journeys, use the [walkthrough index](walkthrough-index.md):
[Demo](walkthrough-demo.md), [Sandbox](walkthrough-sandbox.md), and
[Pilot](walkthrough-pilot.md).

For the optional local documentation navigation layer, read the
[docs-site guide](docs-site.md) and [documentation map](docs-navigation.md). It is not published
by this repository, and Demo Mode does not require MkDocs.

For maintainer-only publication preparation, see [Release readiness](release-readiness.md),
[Release checklist](release-checklist.md), and
[Release notes template](release-notes-template.md). These publish nothing.

For the current public handoff, use [Final public readiness](final-public-readiness.md), the
[final checklist](final-readiness-checklist.md), and the
[H2 maintainer cleanup note](maintainer-review-fix-pack.md).

For a product-facing Demo view, use the [Intake Review Workspace](intake-review-workspace.md).
It reviews sanitized local records only and performs no Procore write or lifecycle transition.

The [Intake lifecycle status flow](intake-lifecycle-status-flow.md) adds audited local state
changes only. Local status does not update Procore and is not an approval, compliance decision,
or external communication.

- [First-run checklist](first-run-checklist.md)
- [Local installer guide](local-installer-guide.md)
- [Setup troubleshooting guide](setup-troubleshooting-guide.md)
- [Setup experience review](setup-experience-review.md)
- [Command reference](command-reference.md)
- [Troubleshooting](troubleshooting.md)
- [Public usability audit](public-usability-audit.md)

- [Demo → Sandbox → Pilot](sandbox-to-pilot-flow.md)
- [Sandbox onboarding](sandbox-onboarding.md)
- [Pilot preflight](pilot-preflight.md)

This is the documentation home for Procore Intake Bridge. The runtime is fixture/mock by default,
live Procore access is disabled by default, and the project performs no Procore writes.

## Getting started

- [README and quick start](../README.md)
- [Safe demo flow](../examples/demo-flow.md)
- [Examples index](../examples/README.md)
- [Project status](project-status.md)
- [Manually gated sandbox smoke tests](sandbox-smoke-tests.md)
- [Secret management](secret-management.md)
- [Database migrations](database-migrations.md)
- [Database providers](database-providers.md)
- [PostgreSQL readiness](postgres-readiness.md)
- [PostgreSQL runtime operations](postgres-runtime-operations.md)
- [PostgreSQL connection pooling](postgres-connection-pooling.md)
- [PostgreSQL migration runbook](postgres-migration-runbook.md)
- [PostgreSQL backup and restore drills](postgres-backup-restore-drills.md)
- [Hosted deployment templates](hosted-deployment-templates.md)
- [Docker VPS hosting](docker-vps-hosting.md)
- [Managed PaaS hosting](managed-paas-hosting.md)
- [Container platform hosting](container-platform-hosting.md)
- [Cloud platform hosting](cloud-platform-hosting.md)
- [HTTPS webhook production planning](https-webhook-production-planning.md)
- [Webhook ingress planning](webhook-ingress-planning.md)
- [TLS and DNS planning](tls-dns-planning.md)
- [Webhook disable and rollback](webhook-disable-rollback.md)
- [Migration execution plan](migration-execution-plan.md)
- [Backup and restore plan](backup-restore-plan.md)

## Design and workflows

- [Architecture](architecture.md)
- [DMSA onboarding](dmsa-onboarding.md)
- [DMSA credential profiles](dmsa-credential-profiles.md)
- [Permissions checklist](permissions-checklist.md)
- [Polling worker](polling-worker.md)
- [Webhooks](webhooks.md)
- [Attachment storage](attachment-storage.md)
- [Attachment storage backends](attachment-storage-backends.md)
- [Storage providers](storage-providers.md)
- [Onboarding packets](onboarding-packets.md)
- [Admin dashboard](admin-dashboard.md)
- [Admin authentication](admin-authentication.md)

## Operations and safety

- [Deployment hardening](deployment-hardening.md)
- [Deployment recipes](deployment-recipes.md)
- [HTTPS and webhook ingress](https-webhook-ingress.md)
- [Deployment cutover](deployment-cutover.md)
- [Deployment backup and rollback](deployment-backup-rollback.md)
- [Operations runbook](operations-runbook.md)
- [Safety model](safety-model.md)
- [Roadmap](roadmap.md)
- [Public launch checklist](public-launch-checklist.md)

The GC/Owner controls private DMSA installation and permissions. This independent project is not
affiliated with or endorsed by Procore Technologies and carries no production guarantee.
- [Webhook production verification](webhook-production-verification.md)
- [Customer-specific deployment pattern](customer-deployment-pattern.md)
- [Operator diagnostics and support bundles](operator-diagnostics.md)
- [Pilot readiness gate](pilot-readiness-gate.md)
- [Private pilot evidence workspace](private-pilot-evidence.md)
- [Evidence review and expiry](evidence-review-expiry.md)
- [Private pilot approval packet](pilot-approval-packet.md)
# Usage modes

- [Three usage modes](usage-modes.md)
- [Demo quickstart](quickstart-demo.md)
- [Sandbox mode](sandbox-mode.md)
- [Pilot mode](pilot-mode.md)
- [Private workspace bootstrap](private-workspace-bootstrap.md)
- [Secret providers](secret-providers.md)

Real credentials, customer data, evidence, approvals, generated output, and private workspace
files must not be committed. Best next command: `make start`.
## Final maintainer review

See [Final public readiness](final-public-readiness.md) before deciding the next private step.
The audit performs no live operation, keeps private values and real reports outside Git, and is not
release, production, or pilot approval.
# Operator triage

The [Operator Triage Queue](operator-triage-queue.md) is a GET-only local projection over
sanitized intake and lifecycle data. Its score only controls sorting.

The [Attachment Review and Manifest UX](attachment-review-manifest-ux.md) provides a GET-only,
metadata-only view of sanitized local manifest status.

The [Operator Export Pack](operator-export-pack.md) renders ignored local JSON, Markdown, and CSV
summaries without adding a public export route.
# Phase H8 product cockpit

The [Product Dashboard](product-dashboard.md) connects the existing local review, lifecycle,
triage, attachment metadata, and command-only export guidance. It is read-oriented and makes no
Procore writes or calls.

The [Demo Product Walkthrough](demo-product-walkthrough.md) and
[evaluation checklist](demo-evaluation-checklist.md) connect the complete fake-data-only public
journey without live operations.

Use the [Security Threat Model](security-threat-model.md), [boundary map](security-boundary-map.md),
and [review checklist](security-review-checklist.md) for offline security analysis.

Use the [Auth / Permission Boundary Audit](auth-permission-boundary-audit.md),
[auth map](auth-boundary-map.md), and
[permission checklist](permission-boundary-checklist.md) to review existing route and command
protections without adding an auth provider or performing live permission checks.

Use the [Webhook Replay and Signature Hardening Review](webhook-replay-signature-hardening.md),
[signature boundary](webhook-signature-boundary.md), and
[replay checklist](webhook-replay-checklist.md) for offline fake-fixture review.
