# Demo → Sandbox → Pilot

Demo is the default safe path. Sandbox and Pilot are private/operator-controlled, and all real
credentials, evidence, approvals, and outputs stay outside Git. What to run next:
`make sandbox-to-pilot-plan`.

D5 connects the repository's existing readiness tools into one public-safe order of operations.
The flow is local evaluation only: it makes no automatic Procore, secret-manager, storage,
database, DNS, TLS, cloud, webhook-registration, migration, or deployment calls.

## Exact order

1. **Demo:** run `make demo`, then `make doctor`. This fixture-only path needs no credentials,
   external database, storage provider, deployment, or private workspace.
2. **Private boundary:** run `make init-private-workspace`, then
   `make validate-private-workspace` and `make private-workspace-git-safety`.
3. **Sandbox onboarding:** place DMSA secret references, allowed company/project scope, admin
   authentication posture, and permission review records in that ignored workspace. Run
   `make sandbox-onboarding-check`.
4. **Manual smoke:** after separate authorization, use the B1 manually gated harness. D5 never
   runs it. Store only `SANDBOX_SMOKE_REF_PLACEHOLDER`-shaped metadata in public profiles and the
   actual result reference privately.
5. **Pilot preflight:** validate D1 secrets, D2 storage, D3 PostgreSQL/migration planning, D4
   deployment/HTTPS/backup/rollback, B7 customer deployment, B8 diagnostics, B9 readiness, C1
   evidence metadata, C2 review/expiry, and C3 approval-packet preparation.
6. **Private review and launch hold:** run `make pilot-preflight`. Even
   `pilot_ready_for_private_review` is not approval. Authorized people must review actual private
   evidence and signoff outside this public repository.

Start with `make sandbox-to-pilot-plan` or print a placeholder profile with
`make sandbox-pilot-template`. Generated artifacts belong under ignored
`sandbox-pilot-output/`; never commit them.

Real identifiers, people, emails, phone numbers, domains, URLs, credentials, database details,
infrastructure identifiers, evidence, reports, logs, certificates, approvals, and downloaded
files must remain private. Future work is the separately authorized execution of an actual
controlled pilot; D5 neither performs nor approves that work.
