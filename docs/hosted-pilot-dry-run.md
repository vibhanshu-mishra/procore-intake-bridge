# Hosted pilot operations dry run

Phase G6 combines opaque planning references from G1–G5 with Sandbox evidence, pilot readiness,
rollback, monitoring, diagnostics, and support references. It is a public-safe checklist system,
not deployment automation.

The dry run is not a launch and is not pilot approval. It makes no live operation, Procore,
database, cloud, DNS, TLS, webhook, or deployment call. It does not read private reports or
evidence contents by default; it validates placeholder reference labels only.

```bash
make hosted-pilot-dry-run-template
make hosted-pilot-dry-run-check
make hosted-pilot-dry-run-matrix
make hosted-pilot-dry-run-artifact-check
```

The artifact check uses a temporary directory and cleans it. Real hosted and pilot preparation
remains private and manual. A human must review the resulting reference map and blockers before
any separately authorized launch process.

## How G1–G5 come together

| Phase | Dry-run input |
|---|---|
| G1 | Cloud secret-provider plan reference |
| G2 | Cloud storage-provider plan reference |
| G3 | PostgreSQL runtime plan reference |
| G4 | Hosted deployment-template plan reference |
| G5 | HTTPS/webhook ingress plan reference |

These inputs prove only that placeholder references are structurally present. They do not prove
that linked plans are correct, that private evidence exists, or that a hosted pilot is ready.
## H1 handoff

Final public readiness checks that this dry-run boundary is documented and discoverable. H1 does
not open private reports or run operations and is not release, production, or pilot approval.
