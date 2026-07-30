# Deployment cutover

The D4 cutover checklist is a planning aid. Before a private cutover, confirm an approved operator,
maintenance window, database migration posture, backup and restore evidence, diagnostics,
HTTPS/ingress review, rollback triggers, and a private go/no-go decision.

Generating the checklist performs no deployment, migration, DNS change, certificate operation,
webhook registration, or external call. A completed checklist is not production approval.

Hosted template generation is not cutover. It creates no resources, changes no DNS, issues no
certificate, pushes no image, and grants no go-live decision. Adapt the checklist privately and
retain the manual cutover and rollback boundary.
