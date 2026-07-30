# Examples

The `postgres-runtime/` examples are placeholder-only private-operation planning aids. They perform
no database connection, migration, backup, or restore.

The `hosted-deployment-templates/` directory contains placeholder-only conceptual platform
profiles and snippets. They are not ready-to-run deployments.

All examples are synthetic, local, and fixture/mock-only.

- [Safe demo flow](demo-flow.md): exercise health, local profiles, dry-runs, onboarding preview,
  masked admin output, and readiness reporting.
- [`onboarding/`](onboarding/): fake GC/Owner packet output examples containing placeholders only.

No live Procore credentials, private identifiers, signed URLs, or network access are required.

The `https-webhook-planning/` examples contain only public-safe planning references. They perform
no DNS/TLS/ACME check, public URL verification, certificate generation, or webhook registration.

The `hosted-pilot-dry-run/` examples connect opaque G1–G5 and pilot-operations references without
opening linked evidence or claiming launch approval.

The `final-public-readiness/` examples illustrate maintainer-review output and checklist wording.
They contain placeholders only and do not represent release, production, or pilot approval.

Provider, PostgreSQL, hosted-template, webhook-planning, dry-run, and final-readiness examples are
conceptual inputs—not ready-to-deploy configuration. Private values and generated outputs stay
outside Git.
