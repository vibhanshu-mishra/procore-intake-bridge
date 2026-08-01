# Documentation Reader Paths

Choose one path and follow its links in order. These are local reading sequences, not automation.

## First-time evaluator

1. [Documentation home](index.md)
2. [Local installer guide](local-installer-guide.md)
3. [Demo data seed and reset](demo-data-seed-reset.md)
4. [Demo product walkthrough](demo-product-walkthrough.md)
5. [Product dashboard](product-dashboard.md)
6. [API route reference](api-route-reference.md)
7. [Hosted UI preparation](hosted-ui-preparation.md)

## Demo user

[Quickstart](quickstart-site.md) → [Demo walkthrough](walkthrough-demo.md) →
[Demo seed/reset](demo-data-seed-reset.md) → [Intake review](intake-review-workspace.md) →
[Lifecycle flow](intake-lifecycle-status-flow.md) → [Triage](operator-triage-queue.md) →
[Attachment metadata](attachment-review-manifest-ux.md).

## Sandbox or Pilot preparer

Read [usage modes](usage-modes.md), then follow the Sandbox or Pilot path in
[documentation navigation](docs-navigation.md). These modes are private, manually gated, and do
not inherit Demo readiness or approval.

## Hosted preparer

[Hosted UI preparation](hosted-ui-preparation.md) → [private gates](hosted-ui-private-gates.md) →
[hosted deployment templates](hosted-deployment-templates.md) →
[HTTPS/webhook planning](https-webhook-production-planning.md) →
[final security review](final-security-readiness-review.md). This path is planning only.

## Security reviewer

[Threat model](security-threat-model.md) → [auth boundary audit](auth-permission-boundary-audit.md)
→ [security closeout](security-gap-closeout.md) →
[final security review](final-security-readiness-review.md). Private verification remains required.

## Operator, release reviewer, or contributor

- Operator: [operations runbook](operations-runbook.md) → [diagnostics](operator-diagnostics.md).
- Release reviewer: [final public readiness](final-public-readiness.md) →
  [release readiness](release-readiness.md).
- Contributor: [command reference](command-reference.md) → [public usability audit](public-usability-audit.md).

All paths are local-only. They perform no docs deployment and add no GitHub Pages workflow,
external analytics, tracking, search, or CDN asset. Reading a path grants no production, Pilot,
release, deployment, or docs-hosting approval.
