# Customer-specific deployment pattern

Phase B7 provides a local, customer-specific planning profile, readiness validator, and
Markdown/JSON checklist generator. It does not deploy the application, create infrastructure,
connect cloud services or databases, call Procore, expose webhooks, resolve secrets, or claim
production security. The committed example contains fake values only.

## Why use a separate profile

Each future deployment needs an independently reviewed project allowlist, tool scope, admin
authentication plan, webhook posture, storage posture, database/migration plan, recovery plan,
sandbox evidence, and GC/Owner onboarding approval. Keeping those decisions in a validated
planning profile makes blockers visible without mixing private customer details into application
configuration or this public repository.

Profiles contain references, never secret values. DMSA client ID/secret, admin primary/rotation
tokens, webhook secret, and storage bucket fields are opaque placeholder references. Project
company/project IDs and labels must remain obvious placeholders in public examples. Production
plans require token-protected admin access, an explicit non-SQLite database profile, reviewed
migration/backup/rollback plans, explicit hosts, sandbox smoke evidence, onboarding evidence, and
verified B6 documentation assumptions before webhooks are planned. External secret and storage
placeholders remain blockers because they implement no real provider.

## Safe local workflow

```bash
python scripts/print_customer_deployment_template.py
python scripts/validate_customer_deployment_profile.py \
  examples/customer-deployments/example_customer_profile.json
python scripts/validate_customer_deployment_profile.py --strict \
  /path/to/a/private-placeholder-profile.json
python scripts/generate_customer_deployment_artifacts.py \
  examples/customer-deployments/example_customer_profile.json
```

Generation creates these local files beneath the ignored
`customer-output/<safe-profile-name>/` directory:

- `deployment-summary.md`
- `launch-checklist.md`
- `operations-runbook.md`
- `env-template.example`
- `secret-inventory.json`
- `readiness-report.json`

They contain sanitized planning status and secret references only. They must not be committed.
Never put real customer names, domains, IDs, contacts, credentials, signed URLs, private paths,
payloads, logs, or reports into a public profile.

For a future real customer, create and store the private profile in an approved private system,
review each blocker with the customer/GC/Owner, and separately approve infrastructure, ingress,
database, secrets, storage, monitoring, deployment, rollback, and webhook registration. B7 adds
no Terraform, Pulumi, Kubernetes, Helm, CI/CD, cloud SDK, or deployment automation; those remain
future reviewed work.
B8 support bundles must not contain customer profiles, customer-output artifacts, contacts, IDs,
domains, or private paths. They summarize only the global customer-pattern safety posture.
B9 consumes only the B7 customer profile status and a placeholder evidence reference. It never
copies customer-profile contents or treats B7 validation as pilot approval.

C1 can index that placeholder evidence ref for private review, but neither B7 nor C1 stores
private customer profile contents in this public repository.

C2 may track placeholder review and expiry status for the B7 evidence ref. Real customer
configuration, reviewer identities, and approval records remain private.
