# Project status

The public repository has completed phases A1–H7. Phase H3 adds a public-safe, read-only Intake
Review Workspace for sanitized local RFI/Submittal records. It adds no Procore write, lifecycle
transition, approval, assignment, comment, notification, or external call.

Phase H4 adds audited local lifecycle state and history. It permits only exact guarded local
transition routes, makes no Procore/external call, and does not represent approval, compliance,
assignment, or communication.

Phase H5 adds a GET-only operator triage projection with bounded filters and deterministic local
sorting. It does not mutate lifecycle state or represent assignment, approval, compliance,
communication, notification, risk, or a Procore update.

Phase H6 adds metadata-only attachment manifest review without file access, storage-provider
calls, private storage details, filenames, URLs, or attachment contents.

Phase H7 adds ignored local JSON, Markdown, and CSV summary generation with bounded rows,
traversal protection, and CSV formula neutralization. It adds no public export route.

## Current public posture

- Demo Mode is the default and uses synthetic fixtures with local SQLite.
- Sandbox Mode is private and operator-controlled. Live read-only commands are separate,
  manually gated, allowlisted, bounded, and disabled by default.
- Pilot Mode remains private, evidence-backed, reviewed, human-approved, and subject to an
  explicit launch hold.
- Procore write-back routes do not exist.
- Optional cloud secret and storage adapters are disabled by default.
- PostgreSQL planning is offline; live connectivity and status probes are separate and disabled
  by default.
- Hosted deployment profiles are conceptual templates, not deployment automation.
- HTTPS/webhook planning performs no public endpoint check or webhook registration.
- The hosted pilot dry run validates opaque references only and grants no launch approval.
- Final public readiness is a maintainer-review aid, not release, production, or pilot approval.

## Completed capability groups

- **A1–A9:** backend foundation, credential profiles, polling, webhooks, attachments, onboarding,
  admin UI, deployment hardening, and public repository polish.
- **B1–B9:** manually gated Sandbox smoke, provider contracts, migrations, admin access, storage,
  synthetic webhook verification, customer planning, diagnostics, and pilot readiness.
- **C1–C5:** private evidence patterns, review/expiry, approval packets, three-mode onboarding,
  and ignored private-workspace scaffolding.
- **D1–D5:** environment/file secret resolution, local/cloud storage boundaries, PostgreSQL
  readiness, deployment recipes, and the offline Sandbox-to-Pilot flow.
- **E1–E5:** public usability, command consolidation, walkthroughs, release review, and the
  local-only documentation-site foundation.
- **F1–F3:** Sandbox smoke UX, bounded read validation, and opaque evidence linkage.
- **G1–G6:** optional cloud secret/storage adapters, PostgreSQL operations polish, hosted
  templates, HTTPS/webhook planning, and the hosted pilot dry-run pack.
- **H1:** final public repository readiness inspection and maintainer handoff.
- **H2:** maintainer-review documentation, command-discovery, and audit cleanup.
- **H3:** GET-only local intake review, safe source/manifest context, and priority signals.
- **H4:** transactional local status state/history with bounded reasons and masked actors.
- **H5:** read-only operator triage buckets and deterministic local sorting.
- **H6:** read-only attachment manifest metadata summaries and detail views.
- **H7:** local sanitized summary exports for H3–H6 operator metadata.

## Known limitations

The repository is not production-ready and does not claim production security completion. Real
tenant identity and access
controls, customer-specific provider configuration, production database operations, deployment,
monitoring, evidence, approvals, and launch operations require separate private implementation
and review.

Passing public checks validates repository posture only. It does not prove external reachability,
provider permissions, database recoverability, webhook registration, release approval, production
approval, or pilot approval.

Procore Intake Bridge is independent and is not affiliated with, endorsed by, certified by, or
officially supported by Procore.

## Maintainer commands

```bash
make quality
make safety-check
make docs-site-check
make release-readiness
make final-readiness
```

Private values, generated operational outputs, and real reports stay outside Git.
# Phase H8

Admin Dashboard Product Polish is implemented as a protected GET-only local cockpit. It adds
safe navigation and aggregate visibility without adding product workflows or external behavior.

Phase H9 Demo Product Walkthrough Pack is complete as a fake-data-only, offline maintainer
evaluation flow across the existing H3–H8 product surfaces.

Phase I1 Security Threat Model is complete as an offline, placeholder-safe review layer.

Phase I2 Auth / Permission Boundary Audit is complete as an offline mapping of existing public,
admin-guarded, webhook-signature, local-only, and manually gated surfaces.

Phase I3 Webhook Replay and Signature Hardening Review is complete as an offline fake-fixture
review with explicit needs-review findings for freshness, replay access, and runtime enforcement.
