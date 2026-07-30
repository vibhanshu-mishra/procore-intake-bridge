# Documentation navigation map

Cloud storage guidance starts at [Optional cloud storage providers](cloud-storage-providers.md),
with S3, Azure Blob, and GCS pages under **Providers and Infrastructure**.

Cloud secret guidance begins at [Optional cloud secret providers](cloud-secret-providers.md), with
AWS, Azure, and GCP pages under **Providers and Infrastructure**.

PostgreSQL guidance continues from [readiness](postgres-readiness.md) to
[runtime operations](postgres-runtime-operations.md), [pooling](postgres-connection-pooling.md),
[migration operations](postgres-migration-runbook.md), and
[backup/restore drills](postgres-backup-restore-drills.md).

Hosted planning starts at [hosted deployment templates](hosted-deployment-templates.md), followed
by [Docker VPS](docker-vps-hosting.md), [managed PaaS](managed-paas-hosting.md),
[generic container platforms](container-platform-hosting.md), and
[cloud platform styles](cloud-platform-hosting.md). All are conceptual and non-deploying.

Webhook production preparation continues through
[HTTPS webhook planning](https-webhook-production-planning.md),
[ingress planning](webhook-ingress-planning.md), [TLS/DNS planning](tls-dns-planning.md), and
[disable/rollback planning](webhook-disable-rollback.md). None performs a live check or
registration.

Use this reading order; later sections are needed only for the selected journey.

## 1. Start here

1. [Quickstart](quickstart-site.md)
2. [Command reference](command-reference.md)
3. [Troubleshooting](troubleshooting.md)
4. [Usage modes](usage-modes.md)

## 2. Choose a journey

- **Demo:** [Demo quickstart](quickstart-demo.md) → [Demo walkthrough](walkthrough-demo.md)
  → [Intake Review Workspace](intake-review-workspace.md)
  → [Intake lifecycle status flow](intake-lifecycle-status-flow.md)
- **Sandbox:** [Sandbox mode](sandbox-mode.md) → [Sandbox onboarding](sandbox-onboarding.md) →
  [Sandbox walkthrough](walkthrough-sandbox.md) → [Sandbox smoke UX](sandbox-smoke-ux.md) →
  [Sandbox read validation](sandbox-read-validation.md) →
  [Sandbox read evidence](sandbox-read-evidence.md) →
  [Sandbox evidence linkage](sandbox-evidence-linkage.md) →
  [Sandbox evidence to Pilot](sandbox-evidence-to-pilot.md)
- **Pilot:** [Pilot mode](pilot-mode.md) → [Pilot preflight](pilot-preflight.md) →
  [Pilot walkthrough](walkthrough-pilot.md) → [Pilot readiness](pilot-readiness-gate.md)

Demo is the default safe journey. Sandbox and Pilot are optional, private, operator-controlled
journeys. Documentation does not run their live or deployment actions.

## 3. Prepare private providers only when needed

Read [secret providers](secret-providers.md), [storage providers](storage-providers.md),
[database providers](database-providers.md), and [deployment recipes](deployment-recipes.md).
All real configuration stays private and outside Git.

## 4. Operate and review

Use the [operations runbook](operations-runbook.md), [operator diagnostics](operator-diagnostics.md),
[safety model](safety-model.md), and [public usability audit](public-usability-audit.md).
Maintainers may then consult [release readiness](release-readiness.md).

This map is a local documentation aid. It publishes nothing and adds no GitHub Pages or hosting
automation.
## Hosted pilot rehearsal

Start with [Hosted pilot dry run](hosted-pilot-dry-run.md), then use
[Pilot operations rehearsal](pilot-operations-rehearsal.md) and the
[Hosted pilot evidence map](hosted-pilot-evidence-map.md). These reference-only guides perform no
live operation and do not grant launch or pilot approval.
## Final repository review

Use [Final public readiness](final-public-readiness.md), the
[Public repository handoff](public-repository-handoff.md), and the
[Final readiness checklist](final-readiness-checklist.md). These guides make no live calls and
grant no release, production, or pilot approval.

The [H2 maintainer review fix pack](maintainer-review-fix-pack.md) records the bounded cleanup
performed after H1. It adds no runtime or live capability.
- [Operator Triage Queue](operator-triage-queue.md): GET-only local sorting and bucket projection
  over sanitized H3/H4 data.
- [Attachment Review and Manifest UX](attachment-review-manifest-ux.md): metadata-only local
  manifest inspection with no file access.
- [Operator Export Pack](operator-export-pack.md): local sanitized JSON, Markdown, and CSV
  summaries kept outside Git.
# H8

- [Product Dashboard](product-dashboard.md): local product cockpit, safe cards, navigation, and
  Demo/Sandbox/Pilot boundary guidance.

- [Demo Product Walkthrough](demo-product-walkthrough.md): complete fake-data product tour.
- [Demo Evaluation Checklist](demo-evaluation-checklist.md): maintainer evaluation boundaries.
