# Documentation navigation map

Phase J7 release-candidate review path:

1. [Release-candidate review](release-candidate-review.md)
2. [Release-candidate checklist](release-candidate-checklist.md)
3. [Release-candidate gap register](release-candidate-gap-register.md)
4. [Release-candidate command plan](release-candidate-command-plan.md)

This is a checklist for later maintainer review of prepared `0.1.0` metadata. It performs no
package/Docker build, publish, tag, release, deployment, workflow change, or approval.

Phase J6 release-metadata path:

1. [Version preparation review](version-prep-review.md)
2. [Package metadata summary](package-metadata-summary.md)
3. [Version source map](version-source-map.md)
4. [Release boundary checklist](release-boundary-checklist.md)

The prepared `0.1.0` target is release-candidate metadata, not a release. This path performs no
build, publish, tag, release, deployment, workflow change, external call, or approval.

J5 consolidates audience-oriented entry points in [Documentation reader paths](docs-reader-paths.md)
and topic ownership in the [Documentation navigation map](docs-navigation-map.md). Use those as the
canonical discovery layer; the detailed journey links below remain the operational reading order.
Local preview is optional. No docs deployment, workflow, analytics, tracking, external search, CDN
asset, or approval is introduced.

Phase J4 hosted UI preparation path:

1. [Hosted UI preparation](hosted-ui-preparation.md)
2. [Hosted UI page inventory](hosted-ui-page-inventory.md)
3. [Hosted UI readiness checklist](hosted-ui-readiness-checklist.md)
4. [Hosted UI private gates](hosted-ui-private-gates.md)

This offline path deploys nothing. Admin/dashboard/review surfaces remain protected, attachment UI
is metadata-only, exports stay command-only, and private infrastructure/security review is required.
No frontend build, external assets, analytics, telemetry, download route, or approval is added.

Phase J3 API documentation path:

1. [API documentation review](api-docs-review.md)
2. [API route reference](api-route-reference.md)
3. [API usage examples](api-usage-examples.md)
4. [Local OpenAPI guide](openapi-local-guide.md)

These guides cover all 81 existing routes through local inspection only. They make no live call,
use no external OpenAPI tooling, and add no product behavior. Public status, protected surfaces,
local lifecycle mutations, signature-bound webhooks, and metadata-only attachment boundaries stay
explicit. No export download, file-serving, Procore write-back, or operational approval is added.

Phase J2 Demo data path:

1. [Demo data seed and reset](demo-data-seed-reset.md)
2. [Demo seed plan](demo-seed-plan.md)
3. [Demo reset guide](demo-reset-guide.md)

These guides cover deterministic fake-only data in local SQLite. No Procore credential or call,
cloud service, or external database is needed. `make try-demo` is non-destructive; only the exact-
confirmation reset affects demo-marked records. Private workspace, Sandbox, Pilot, Hosted, cloud,
and customer data remain untouched, and no production, Pilot, or release approval is implied.

Phase J1 local setup path:

1. [Local installer guide](local-installer-guide.md)
2. [First-run checklist](first-run-checklist.md)
3. [Setup troubleshooting guide](setup-troubleshooting-guide.md)
4. [Setup experience review](setup-experience-review.md)

First create `.venv`, second activate it, and third install local development dependencies; next
run `make start` and `make try-demo`. Demo requires no Procore credentials, other secrets, cloud
service, or external database. Sandbox, Pilot, and Hosted are separate gated paths. Setup does no
build, publish, release, or deployment and grants no operational approval.

Phase I9 closeout path:

1. [Security gap closeout](security-gap-closeout.md)
2. [Privacy review template](privacy-review-template.md)
3. [Encryption-at-rest guidance](encryption-at-rest-guidance.md)
4. [Private security action register](private-security-action-register.md)
5. [Known limitations closeout](known-limitations-closeout.md)

This path is offline guidance only. It performs no scanner, external or Procore call, encryption,
retention enforcement, deletion/purge, or notification and grants no compliance, certification,
or operational approval. Private review remains required.

Phase I7: [review](incident-response-forensics.md), [runbook](incident-runbook.md), [audit map](audit-log-boundary-map.md), and [evidence checklist](forensics-evidence-checklist.md).

Phase I8: [final review](final-security-readiness-review.md),
[readiness summary](security-readiness-summary.md), [gap register](security-gap-register.md), and
[private review checklist](private-security-review-checklist.md). I8 aggregates I1–I7 offline;
private security review remains required and no approval or certification is granted.

Phase I6: [review](dependency-supply-chain-security.md), [dependency map](dependency-boundary-map.md), [package map](package-surface-map.md), and [checklist](supply-chain-checklist.md).

Phase I5: [review](secrets-storage-db-security-review.md), [secret map](secret-boundary-map.md), [storage map](storage-boundary-map.md), [database map](database-boundary-map.md), and [checklist](infra-security-checklist.md).

Phase I4: [policy](data-retention-redaction-policy.md), [retention map](data-retention-map.md), [redaction map](redaction-boundary-map.md), and [handling checklist](data-handling-checklist.md).

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

- [Security Threat Model](security-threat-model.md): offline categories, controls, and gaps.
- [Security Boundary Map](security-boundary-map.md): public/private trust boundaries.
- [Security Review Checklist](security-review-checklist.md): private follow-up boundaries.
- [Auth / Permission Boundary Audit](auth-permission-boundary-audit.md): offline route and command
  protection audit.
- [Auth Boundary Map](auth-boundary-map.md): route classes, protection types, and method risks.
- [Permission Boundary Checklist](permission-boundary-checklist.md): offline maintainer checks.
- [Webhook Replay and Signature Hardening](webhook-replay-signature-hardening.md): offline
  signature, freshness, deduplication, replay, and redaction review.
- [Webhook Signature Boundary](webhook-signature-boundary.md): exact-request-byte and digest
  comparison expectations.
- [Webhook Replay Checklist](webhook-replay-checklist.md): private hardening follow-up.
