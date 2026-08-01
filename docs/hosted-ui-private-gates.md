# Hosted UI Private Gates

Phase J4 intentionally leaves hosted operation behind private gates. Before a maintainer exposes
any candidate surface, private reviewers must verify:

1. Hosted infrastructure, network ingress, DNS/TLS, rollback, and backup ownership.
2. Authentication and authorization appropriate to real users; existing local admin-token behavior
   is not by itself a hosted identity system.
3. Private secret, database, storage, attachment, logging, monitoring, and incident-response design.
4. Customer-data handling, privacy, retention, notification, legal, and contractual obligations.
5. Route exposure: dashboards/review remain protected, lifecycle stays local-only, webhook ingress
   stays signature-bound, attachments stay metadata-only, and exports stay command-only.
6. Operational ownership, support contacts, evidence custody, Pilot scope, and explicit rollback.

Do not put private findings, identities, domains, URLs, credentials, infrastructure IDs, reports,
or approval records in this repository. J4 does not perform or approve deployment. It adds no
external assets, frontend build, analytics, telemetry, public download, or file-serving behavior.

The hosted path remains `hosted_needs_private_review`; production, Pilot, release, deployment,
launch, compliance, certification, and Procore approval are outside this public review.
