# Documentation

Follow this beginner order: [Quickstart](../QUICKSTART.md), [usage modes](usage-modes.md),
[command reference](command-reference.md), [Demo walkthrough](quickstart-demo.md), then
[Sandbox](sandbox-mode.md) or [Pilot](pilot-mode.md). Start with `make start`.

For the complete guided journeys, use the [walkthrough index](walkthrough-index.md):
[Demo](walkthrough-demo.md), [Sandbox](walkthrough-sandbox.md), and
[Pilot](walkthrough-pilot.md).

For the optional local documentation navigation layer, read the
[docs-site guide](docs-site.md) and [documentation map](docs-navigation.md). It is not published
by this repository, and Demo Mode does not require MkDocs.

For future maintainer-only publication preparation, see [Release readiness](release-readiness.md),
[Release checklist](release-checklist.md), and
[Release notes template](release-notes-template.md). These publish nothing.

- [First-run checklist](first-run-checklist.md)
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
