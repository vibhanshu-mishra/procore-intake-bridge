# Security Threat Model

I7 maps offline incident scenarios, audit-log metadata boundaries, and private evidence references.

I6 maps dependency declarations, optional extras, package surfaces, generated artifacts, and automation boundaries.

I5 adds offline secret-provider, storage-provider, database-runtime, migration, and backup/restore planning boundaries without exercising them.

Phase I4 extends this offline review with data classifications, retention boundaries, and redaction boundaries. It is not legal compliance certification and performs no live scan or deletion.

Phase I1 is an offline, public-safe threat-modeling layer. It inspects local repository files
only and runs no live security scanner, external call, Procore call, database connection, cloud
operation, deployment, or release.

It covers spoofing, tampering, repudiation, information disclosure, denial of service, elevation
of privilege, supply chain, misconfiguration, data retention, public/private separation, and
live-operation separation across public runtime, local data, admin/review, provider, external
API, hosted preparation, private review, and generated-output trust boundaries.

Existing controls include offline public/route audits, secret references, metadata-only review,
ignored outputs, bounded local lifecycle changes, and manual live-operation gates.
Environment-specific configuration, credentials, evidence, and risk acceptance still require
private security review.

```bash
make security-threat-model
make security-boundary-map
make security-review-checklist
```

I1 does not provide production authorization, security or compliance certification, SOC 2, ISO,
HIPAA, launch authorization, or Pilot authorization. Later I-series work may deepen offline risk
analysis while preserving these boundaries.

I2 applies the [Auth / Permission Boundary Audit](auth-permission-boundary-audit.md) to the route
and command surfaces named here. It uses existing guard structure only and adds no login, SSO,
OAuth, RBAC, account, cookie, or session capability.

I3 deepens the webhook-ingress and event-queue scenarios through an
[offline hardening review](webhook-replay-signature-hardening.md).

I8 aggregates this model with I2–I7 and the repository safety/readiness checks in the
[Final Security Readiness Review](final-security-readiness-review.md). The aggregation remains
offline: no scanner, external call, Procore call, deployment, release, or build occurs. Public
maintainer-review readiness is not production approval or certification, and private security
review remains required.
