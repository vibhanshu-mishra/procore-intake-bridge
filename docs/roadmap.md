# Roadmap

## J10 — post-release planning only

J10 records candidate follow-up work without committing to a schedule. “Post-release” means after
a future human-approved `0.1.0` release; no release happened in J10. See the [post-release roadmap](post-release-roadmap.md),
[known-limitations register](known-limitations-register.md), [future-work backlog](future-work-backlog.md),
[private-review backlog](private-review-backlog.md), and [pre-tag reminder](pre-tag-reminder-checklist.md).
J10 performs no release, build, publish, upload, tag, deploy, issue filing, ticket creation, or
approval. Maintainer review and private review remain required.

## J8 versioned 0.1.0 release handoff — completed

J8 adds a public, offline handoff layer for prepared `0.1.0` metadata: release notes draft,
included-scope and known-limitations summary, maintainer decision checklist, evidence matrix,
and safe post-release checklist. It does not perform a package/Docker build, publish, upload, tag,
release, docs deployment, application deployment, external call, or workflow change. Actual
release work and maintainer authorization remain future private actions.

## J7 release-candidate checklist

J7 completes a public, offline checklist for later maintainer review of prepared `0.1.0` metadata.
Artifact build/inspection, signing, publication, tagging, release authorization, and deployment
remain later controlled work. No workflow or approval is added.

## J6 package metadata and version preparation

J6 prepares `0.1.0` metadata and the inputs for a future maintainer release-candidate review. A real
build, artifact inspection, signing decision, registry/publishing decision, tag, release, and
deployment remain future private actions. J6 adds no workflow automation and grants no approval.

## J5 hosted documentation-site polish

J5 completes local handbook navigation for evaluator, Demo, Sandbox, Pilot, Hosted, security,
operator, release, and contributor audiences. Future hosting remains separate work: J5 adds no
deployment workflow, external analytics/tracking/search/CDN service, publication, or approval.

## J4 hosted UI preparation

J4 establishes an offline page inventory, route matrix, readiness checklist, and private-gate map
for a possible future hosted evaluation. No hosting, frontend build, external asset, analytics,
telemetry, download, or file-serving behavior is added. Hosted operation remains future private work
and receives no production, Pilot, release, or deployment approval.

## J3 API documentation and route reference

J3 completes a public-safe offline reference for all 81 current routes, including method, purpose,
class, protection, and method risk. Local OpenAPI guidance uses fake data after starting the local
app. No live call, external tooling, new product behavior, public export/file serving, Procore
write-back, or operational approval is included.

## J2 local Demo data experience

J2 makes local Demo Mode repeatable through deterministic fake-only seed data, idempotent seeding,
non-destructive plans and inventory checks, and exact-confirmation reset of demo-marked local
SQLite records. It leaves private workspace, Sandbox, Pilot, Hosted, cloud, external databases,
and customer data untouched. `make try-demo` remains non-destructive. J2 makes no Procore call and
grants no production, Pilot, release, deployment, or Procore approval.

## J1 local setup experience

J1 improves public maintainer onboarding without changing product behavior. It documents Git,
Python 3.12+, pip, Make, `.venv`, local dependency installation, and the exact first/second/third
commands. Demo remains credential-free, cloud-free, and external-database-free; Sandbox, Pilot,
and Hosted remain separate and gated. J1 adds no package or Docker build, publish, release,
deployment, or operational approval.

## I9 closeout and future work

The public I9 closeout documents remaining gaps without implementing them. Future work may include
retention enforcement, a complete audit-log design, notifications/alerting, and deployment-specific
encryption verification, but only through separately reviewed product or private-infrastructure
work. The privacy template remains a legal-review aid. I9 itself is offline and grants no
compliance, certification, production, pilot, release, or deployment approval.

- Phase I7: Incident Response / Audit Log / Forensics Pack — offline boundaries only.

- Phase I8: Final Security Readiness Review — offline I1–I7 aggregation complete; authorized
  private security review remains required, with no production, pilot, release, legal,
  compliance, or certification approval.

- Phase I6: Dependency and Supply Chain Security Pack — offline review only.

- Phase I5: Secrets / Storage / DB Security Review — offline public-safe review layer; no live infrastructure operations.

- Phase I4: Data Retention and Redaction Policy — offline public-safe mapping and validation; destructive enforcement remains out of scope.

Phases A1–H7 are implemented in the public repository. H3 provides local intake review, H4 adds
audited local-only lifecycle state, H5 adds local triage, and H6 adds metadata-only attachment
manifest review.

## Completed public phases

- **A:** local-first intake foundation, read-only integration boundaries, onboarding, admin
  visibility, and repository safety.
- **B:** manually gated Sandbox checks, provider abstractions, migration hardening, authenticated
  admin access, diagnostics, and pilot-readiness planning.
- **C:** private evidence, review/expiry, approval-packet, mode guidance, and workspace patterns.
- **D:** real environment/file and local-storage adapters, optional cloud boundaries, PostgreSQL
  readiness, deployment recipes, and offline Sandbox-to-Pilot planning.
- **E:** usability, command UX, guided walkthroughs, advisory release readiness, and local docs
  navigation.
- **F:** improved Sandbox smoke UX, bounded read validation, and evidence linkage.
- **G:** production-shaped optional provider implementations, PostgreSQL operations guidance,
  hosted templates, HTTPS/webhook planning, and hosted pilot rehearsal.
- **H1:** final public repository readiness audit and maintainer handoff.
- **H2:** maintainer review cleanup.
- **H3:** local Intake Review Workspace with no mutation or Procore write.
- **H4:** local lifecycle state/event history with no Procore or external side effect.
- **H5:** bounded triage filters, buckets, and deterministic sorting with no mutation.
- **H6:** sanitized attachment manifest metadata review with no file or storage access.
- **H7:** ignored local JSON, Markdown, and CSV metadata summary exports.

## Next separately scoped phase

Any later phase must be separately scoped. H5 deliberately adds no assignment, comment,
approval, compliance determination, communication, notification, or Procore update.

## Work that remains private or separately scoped

The following is not implemented as default public automation:

- customer-specific identity, tenant, role, session, and access-audit controls;
- real customer configuration, credentials, identifiers, evidence, and approval records;
- production database migration, backup, restore, and recovery execution;
- infrastructure provisioning, DNS/TLS changes, image publication, and deployment;
- webhook registration or verification against a real public endpoint;
- production monitoring, alerting, incident integrations, and retention operations; and
- release publication, tagging, packaging, production approval, and pilot launch.

Optional cloud secret/storage providers and PostgreSQL live probes remain disabled by default and
require separate private configuration and operator gates. Hosted templates are conceptual, and
the hosted pilot dry run checks opaque references only.

Any later work must preserve GC/Owner control, explicit project allowlists, read-only Procore
behavior, secret redaction, generated-output isolation, and manually confirmed live boundaries.
# H8 — completed

Admin Dashboard Product Polish connects the existing H3–H7 surfaces through a local,
read-oriented cockpit. It adds no Procore capability, export download, or attachment serving.

## H9 — completed

The Demo Product Walkthrough Pack connects clone-to-dashboard evaluation using fake data only.
Private Sandbox and Pilot work remains a later, gated boundary.

## I1 — completed

Security Threat Model documents public controls and private review boundaries. Later I-series
work may deepen offline analysis without live scanners or approval claims.

## I2 — completed

Auth / Permission Boundary Audit maps existing route and command protections offline. It adds no
authentication provider, live permission integration, external call, certification, or approval.

## I3 — completed

Webhook Replay and Signature Hardening Review documents existing local/demo controls and private
hardening gaps without live replay, registration, runtime behavior changes, or approval claims.

## J9 — public maintainer handoff (completed)

J9 supplies the concise public handoff pack for prepared `0.1.0` metadata. It documents what is
included, what is intentionally absent, the safest local commands, private review gates, and the
later manual release decision boundary. No release, package/Docker build, publish/upload, tag, or
deployment happened; no workflow or external integration was added. Maintainer review and private
review remain required, and no production, Pilot, release, or deployment approval is granted.
