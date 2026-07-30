# Private workspace bootstrap

This ignored workspace is only for private/operator-controlled Sandbox or Pilot preparation.
Completed files, generated outputs, evidence, and approvals must not be committed. What to run
next: `make init-private-workspace`, then `make private-workspace-check`. Demo does not need it.

Beginners should reach this step through `make prepare-sandbox` or `make prepare-pilot`; the
workspace is never required by `make start` or `make try-demo`.

D5 adds `flow/` placeholder files for sandbox readiness, pilot readiness, the ordered plan,
preflight, and mandatory launch hold. See [the guided flow](sandbox-to-pilot-flow.md).

Phase C5 adds a public-safe way to initialize an ignored local workspace for Sandbox and Pilot
modes. The public repository remains public: it contains schemas, placeholder templates,
validators, fake examples, scripts, and documentation only. Real customer data never belongs
in GitHub.

## Public and private boundary

Public GitHub may contain fake examples under `examples/private-workspace/`. The ignored private
workspace may contain privately completed reference mappings, allowed sandbox scope, permission
notes, evidence references, reviews, readiness records, approval preparation, launch and rollback
checks, and incident-response notes. It must never contain plaintext secrets or copied evidence
contents, and it must not be committed.

Demo mode does not use a workspace. Sandbox mode uses environment, sandbox, DMSA, permissions,
webhook, and diagnostics placeholders. Pilot mode adds customer-profile, evidence, review/expiry,
readiness, approval, launch, rollback, and incident-response placeholders.

## Local workflow

```bash
make private-workspace-template
make init-private-workspace
make validate-private-workspace
make private-workspace-git-safety
make private-workspace-check
```

Choose a narrower scaffold with `python scripts/init_private_workspace.py --mode sandbox` or
`--mode pilot`. The initializer refuses traversal and existing files unless `--overwrite` is
explicitly supplied. CLI output contains relative paths only.

Generated files include instructions, checklists, and opaque placeholder refs. They exclude real
identities, IDs, domains, contacts, URLs, secret values, database URLs, file contents, payloads,
reports, evidence, signoffs, approval decisions, binary references, and absolute paths.

Fill placeholders only in an authorized local/private environment, validate after edits, and run
the Git safety check before any commit. C5 does not approve a pilot, contact Procore, deploy
infrastructure, or certify production security. Later phases may extend private operational workflows
later, subject to separate scope and authorization.

D1 adds `environment/secrets/README.private.md` plus env/file ref examples. The `secrets/` folder
is ignored and may hold small private text secrets for the file provider; generated templates
contain refs only and never create secret files. D2 adds placeholder-only storage documentation,
provider maps, local-root references, and object references. It never scaffolds stored objects.

D3 adds database URL-reference, PostgreSQL, migration, backup, restore, and rollback placeholders.
It never scaffolds a URL, hostname, credential, dump, backup, log, or absolute path.

D4 adds a `deployment/` folder with recipe, HTTPS, ingress, cutover, backup, rollback, and operator
placeholders. Real domains, certificates, infrastructure IDs, logs, and state remain private.
