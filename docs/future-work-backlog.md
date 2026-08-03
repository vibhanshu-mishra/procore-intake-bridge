# Future Work Backlog (J10)

The backlog is a set of uncommitted candidates for separately scoped future work. It is not a
schedule, a promise, or an active issue/ticket queue. “Post-release” means after a future
human-approved `0.1.0` release. J10 itself has no release, build, publish, upload, tag, deploy,
issue filing, ticket creation, or approval.

## Candidate work

| ID | Candidate | Why it may matter | Required review before scope | Status |
| --- | --- | --- | --- | --- |
| FW-001 | Production identity, tenant isolation, and access-audit design | Protects customer and operator boundaries | Security, privacy, legal, and owner review | Deferred |
| FW-002 | Retention, deletion, and export policy enforcement | Converts advisory policy into controlled behavior | Privacy/legal and data-owner review | Deferred |
| FW-003 | Durable audit log, alerting, and incident workflows | Supports operations and accountability | Security and operations review | Deferred |
| FW-004 | Deployment-specific encryption, key custody, backups, and recovery drills | Establishes infrastructure evidence | Infrastructure and security review | Deferred |
| FW-005 | Supported provider/version policy and dependency maintenance | Makes support expectations explicit | Supply-chain and maintainer review | Deferred |
| FW-006 | Product decision on any write-back or communication capability | Prevents accidental expansion of the read-only boundary | Product, security, and Procore-owner review | Deferred |

## Focused candidate views

These views keep related candidates together without creating an issue or ticket queue:

- **Productionization:** infrastructure, storage, database, backup, rollback, observability, and
  support-operations design before any production use.
- **Hosted pilot:** hosted identity/isolation, hosted UI, documentation hosting, and pilot evidence
  review before any hosted evaluation.
- **Security future work:** retention and deletion design, encryption-at-rest assessment, complete
  audit-log design, and privacy/legal review.
- **Product improvement:** operator experience, API hardening/versioning, documentation, and
  support guidance after maintainer prioritization.

## Intake and sequencing

For a future candidate, capture a short public summary, an owner placeholder, dependencies, a
rollback or stop condition, and a private evidence reference. A maintainer may reject or defer the
candidate. Do not add credentials, customer identifiers, private paths, live URLs, reports, or
approval records.

No candidate is implemented, assigned, scheduled, or approved by this document. Do not open issues
or tickets from this page. Revisit the [known limitations register](known-limitations-register.md)
and [private review backlog](private-review-backlog.md) before proposing a separately scoped change.
