# Demo Product Walkthrough

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
