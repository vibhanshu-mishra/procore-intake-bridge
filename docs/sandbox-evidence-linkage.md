# Sandbox evidence linkage

Phase F3 links opaque references from private Sandbox smoke and read-validation work into existing
Pilot planning workflows. It does not read source report contents by default, run validation,
resolve secrets, call Procore, or inspect private evidence.

Safe local commands:

```bash
make sandbox-evidence-template
make sandbox-evidence-check
make sandbox-evidence-mapping
make sandbox-evidence-artifact-check
```

The first three commands are non-writing and are included in quality. The artifact check uses a
temporary directory and removes it. Generated local linkage output is ignored.

Profiles contain placeholder refs for Sandbox smoke, read validation, permission review, webhook
review, scope review, and operator review. They also contain reviewer, expiry, renewal,
limitations, and notes placeholders. Validation blocks raw URLs, domains, contacts, IDs, paths,
credentials, signed URLs, certificate/key contents, report filenames and contents, response-like
records, attachment metadata, and approval claims.

Smoke/read-validation results and real opaque refs stay private outside Git. F3 does not prove,
grant, or record Pilot approval. Human evidence review, expiry, renewal, readiness evaluation,
approval review, and launch hold remain separate.

See [Sandbox evidence to Pilot](sandbox-evidence-to-pilot.md) for the C1/C2/B9/C3/D5 mapping.
## G6 handoff

The hosted pilot dry run links the opaque Sandbox evidence reference only. It does not open the
evidence or reports, perform a live operation, or approve a launch or pilot.
