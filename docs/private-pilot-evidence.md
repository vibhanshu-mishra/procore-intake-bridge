# Private pilot evidence

Phase C1 defines a local, metadata-only pattern for organizing private pilot evidence outside this
public repository. It provides strict schemas, a fake manifest, offline validation, and a local
workspace scaffold. It performs no Procore calls, external calls, uploads, evidence collection,
approval, deployment, or production enablement.

## Public and private boundary

No real evidence belongs in this public repo. Public content is limited to fake examples only,
placeholder schemas, validators, tests, and documentation under `examples/private-evidence/`.
Real customer names, domains, contacts, Procore IDs, project names, credentials, URLs, paths,
logs, reports, screenshots, payloads, database files, attachments, and documents must stay
outside GitHub.

A real evidence workspace should live in an organization-approved private document or evidence
system with appropriate access control, retention, audit, and reviewer permissions. C1 does not
select, connect to, or certify such a system.

An evidence ref is an opaque placeholder that lets a B9 gate refer to privately reviewed material
without copying that material into the readiness profile. Acceptable public examples include:

- `EVIDENCE_PLACEHOLDER_001`
- `PRIVATE_EVIDENCE_REF_PLACEHOLDER_SANDBOX_SMOKE`
- `SUPPORT_DIAGNOSTICS_OWNER_PLACEHOLDER`

Blocked content includes real numeric IDs, customer domains, email or phone contacts,
Authorization material, tokens, secrets, signed URLs, absolute paths, `.env` assignments, DB or
storage URLs, raw payloads, raw reports, support bundles, screenshots, binary files, attachments,
and generated private artifacts.

## Local workflow

```bash
python scripts/print_private_evidence_template.py
python scripts/validate_private_evidence_manifest.py \
  examples/private-evidence/example_evidence_manifest.json --strict
python scripts/generate_private_evidence_workspace.py \
  examples/private-evidence/example_evidence_manifest.json \
  --output-root private-evidence-output
```

The scaffold contains a README, manifest template, evidence index, checklist, redaction report,
and artifact manifest. Generated artifacts are ignored by Git. They include only sanitized
placeholder metadata and explicitly exclude evidence contents, real paths, secrets, raw reports,
screenshots, payloads, attachments, and approvals.

## Review and handoff

Before private review, validate the metadata manifest, separately redact the actual material in
the approved private system, grant reviewers minimum necessary access, and share the evidence ref
through an authorized channel. Do not share public repository links to real evidence, raw support
bundles, smoke or webhook reports, credentials, signed URLs, environment files, database exports,
or downloaded attachments.

C1 only organizes references that can support B9 decisions. It does not prove evidence is genuine,
current, complete, approved, or sufficient, and it does not mean a pilot is approved.

Future private work may add an independently reviewed evidence repository, collection process,
retention policy, access audit, redaction review, approval workflow, and evidence expiry handling.
That work requires separate authorization and must remain outside the public repository.
