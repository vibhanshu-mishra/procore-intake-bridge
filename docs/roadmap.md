# Roadmap

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
