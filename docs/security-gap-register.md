# Security Gap Register

Phase I9 adds a separate [closeout and private-action layer](security-gap-closeout.md) that assigns
an implementation level to each gap. Privacy and encryption materials remain templates/guidance;
retention enforcement, a full audit log, and notifications are not added by I9. Private review
remains required and no compliance, certification, or operational approval is granted.

The I8 gap register records sanitized public-review gaps and placeholder references for work that
must be completed privately. Run `make security-gap-register` to print the offline view. No live
scanner, external call, Procore call, deployment, release, package build, notification, log
collection, or evidence collection occurs.

At minimum, the register preserves the private-review boundary for live infrastructure, real
credentials, real customer data, actual legal obligations, provider permissions, release
process, incident contacts, evidence custody, and operational controls. Private findings and
evidence contents stay outside the public repository.

A gap status is review input, not production, pilot, release, deployment, or launch approval. It
does not claim security certification, legal compliance, regulatory compliance, Procore
readiness, endorsement, partnership, or official support.
