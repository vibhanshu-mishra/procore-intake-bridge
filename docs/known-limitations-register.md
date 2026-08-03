# Known Limitations Register (J10)

This register records current public limitations and the review needed to change them. It is
planning material, not a defect tracker. “Post-release” means after a future human-approved
`0.1.0` release; no release has happened in J10.

J10 performs no release, build, publish, upload, tag, deploy, issue filing, ticket creation, or
approval. Maintainer review and private security, legal, privacy, infrastructure, and ownership
review remain required. Do not copy private reports, identities, credentials, domains, logs, or
customer data into this file.

| ID | Limitation | Current public boundary | Follow-up class | Evidence / owner |
| --- | --- | --- | --- | --- |
| KL-001 | Tenant identity, roles, and production access controls are not configured here. | Demo is local and fixture-based; live paths remain separately gated. | Private identity and authorization review | `PRIVATE_REVIEW_REF_PLACEHOLDER` / `OWNER_PLACEHOLDER` |
| KL-002 | Production database operations, recovery evidence, and migration execution are not provided. | Database guidance is offline and local. | Private infrastructure runbook and evidence | `PRIVATE_REVIEW_REF_PLACEHOLDER` / `OWNER_PLACEHOLDER` |
| KL-003 | Retention periods, deletion enforcement, and legal disposition are not implemented. | Policy and redaction guidance is advisory. | Privacy/legal design and implementation review | `PRIVATE_REVIEW_REF_PLACEHOLDER` / `OWNER_PLACEHOLDER` |
| KL-004 | Complete audit-log durability, alerting, and notification delivery are not implemented. | Local lifecycle history is not an operational audit system. | Security and operations design | `PRIVATE_REVIEW_REF_PLACEHOLDER` / `OWNER_PLACEHOLDER` |
| KL-005 | Deployment-specific encryption, key custody, monitoring, and incident evidence are not proven. | Provider and hosting pages are conceptual and non-deploying. | Private infrastructure and security review | `PRIVATE_REVIEW_REF_PLACEHOLDER` / `OWNER_PLACEHOLDER` |
| KL-006 | Procore write-back, approval, assignment, and customer communication are intentionally absent. | The integration boundary is read-only by default. | Separate product scope and authorization | `FUTURE_WORK_REVIEW_PLACEHOLDER` / `OWNER_PLACEHOLDER` |

The same boundaries, stated plainly for review searches, are: **no production approval**, **no
hosted deployment**, **no notifications or alerting**, **no full audit log**, **no retention
enforcement**, **no app-level encryption**, and **no privacy/legal compliance claim**. These are
known limitations, not completed work or commitments.

## Register rules

- Keep status language factual: `known`, `needs private review`, `deferred`, or `separately scoped`.
- Link only to public documents or opaque private references; never paste private evidence.
- A passing local check does not close a limitation or grant production, Pilot, release, deployment,
  legal, privacy, security, or compliance approval.
- Any implementation must be separately specified, reviewed, tested, and documented.

This register does not open issues or tickets and does not claim that any follow-up is complete.
