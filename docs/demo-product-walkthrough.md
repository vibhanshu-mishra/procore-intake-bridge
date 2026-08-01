# Demo Product Walkthrough

Use the J3 [API usage examples](api-usage-examples.md) only with fake/local Demo data. Route-table
inspection makes no live call and uses no external OpenAPI tooling. It adds no public export
download, file-serving, or Procore write-back route and grants no operational approval.

For a repeatable J2 walkthrough, preview and seed deterministic fake local data with
`make demo-seed-plan`, `make demo-seed`, and `make demo-data-check`. The data is local SQLite only
and needs no Procore credential or call, cloud service, or external database. `make try-demo`
remains non-destructive. Reset is optional, affects only demo-marked local records, and requires
`make demo-reset DEMO_RESET_CONFIRMATION="RESET DEMO DATA"`; it cannot touch private workspace,
Sandbox, Pilot, Hosted, cloud, or customer data. No operational approval is implied.

Phase J1 setup for this walkthrough is local-only: first create `.venv`, second activate it, and
third install local development dependencies. Demo requires no Procore credentials, other
secrets, cloud services, or external database. Sandbox, Pilot, and Hosted are separate private,
gated paths. Setup performs no build, publish, release, or deployment and grants no approval.

Phase H9 is a Demo Mode-only maintainer tour built entirely from committed fake data. It performs
no Procore call, external call, live Sandbox validation, external database connection, cloud or
storage-provider operation, attachment file access, webhook operation, deployment, release, or
private report read.

There are no live operations in the H9 walkthrough.

## Walk the product

```bash
make first-run
make try-demo
make demo-product-check
make demo-product-tour
```

Then start the local application and open `/dashboard`:

1. Use the Product Dashboard for safe aggregate context.
2. Open the Intake Review Workspace to inspect sanitized fake intake records.
3. Review local lifecycle labels and bounded transition guidance.
4. Use the Operator Triage Queue as a deterministic local sorting helper.
5. Inspect attachment manifest metadata without opening files.
6. Run `make operator-export-check` for command-only sanitized export validation.
7. Run `make safety-check`, `make final-readiness`, and `make release-readiness`.
8. Stop before Sandbox or Pilot work.

Generated H9 artifacts are optional, ignored, and contain public-safe evaluation material only.
Demo Mode does not establish production readiness, Pilot authorization, compliance
certification, customer reporting, Procore status, endorsement, or official support.

Sandbox and Pilot begin later in a private workspace. Their credentials, evidence, reports,
authorization decisions, and manually gated checks stay outside this public Demo journey.

After the Demo tour, `make security-threat-model` provides offline public-safe security review
input without scanning the environment.
