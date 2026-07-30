# Hosted pilot evidence map

The public G6 evidence map contains opaque placeholder labels only. It connects planning
categories conceptually without opening files, fetching reports, resolving secrets, or querying
services.

Required categories cover cloud secrets, cloud storage, PostgreSQL, hosting, HTTPS/webhooks,
Sandbox smoke, Sandbox read validation, Sandbox evidence linkage, pilot readiness, the approval
packet, rollback, disable, diagnostics, support bundles, monitoring, incident response, and data
handling.

Missing labels produce `needs_review`. Unsafe or non-placeholder values fail closed as `blocked`.
Even a complete map only means it is ready for private human review. It is not launch approval,
pilot approval, or a production-readiness claim, and no live operation occurs.
