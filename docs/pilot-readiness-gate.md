# Pilot readiness gate

The sandbox smoke gate consumes a private, reviewed evidence ref and status. A placeholder or
passing read probe is not pilot approval or production readiness.

D5 consumes this gate as part of [pilot preflight](pilot-preflight.md); neither check grants
approval.

Phase B9 is a local-only, fail-closed go/no-go gate for planning a controlled pilot. It validates
placeholder evidence references and generates sanitized local checklists. It includes no deployment
automation and makes no Procore calls, live sync, infrastructure changes, webhook registration or
exposure, or external service/database connections.

There is no deployment automation in B9.
GO is not production deployment approval.

Decisions mean:

- `GO`: every configured gate passed for this local profile. This is not production deployment
  approval, customer authorization, security certification, or permission to launch.
- `NO_GO`: at least one required evidence or posture gate failed.
- `NEEDS_REVIEW`: no blocker exists, but warnings, unknowns, monitoring work, or known limitations
  remain.
- `BLOCKED`: validation is disabled or a fail-closed safety boundary was triggered.

Production profiles and real-looking IDs are blocked by default. Public profiles must use fake
labels, fake `.local`/`.invalid` domains, placeholder IDs, approval placeholders, and evidence
references only. They must contain no evidence contents, reports, support bundles, logs, payloads,
attachments, contacts, tokens, secrets, Authorization material, signed URLs, or private paths.

## Required evidence categories

The gate covers the B7 customer profile; DMSA onboarding; GC/Owner permissions; private-app
installation; implemented secret provider; token-required admin authentication; database and
migration safety; reviewed attachment storage; B6 documentation/signature/verification when
webhooks are planned; B1 sandbox smoke evidence; B8 diagnostics and support-bundle redaction;
backup and rollback; incident response; data handling; project allowlist/tool scope; operator and
customer approval placeholders; monitoring; and known limitations.

Sandbox smoke may be `not_applicable` only for an explicitly local-only dry-run profile. A
pilot-like staging/sandbox profile cannot use `local_optional` admin authentication or a
SQLite/local database posture. External placeholder secret/storage adapters do not count as

D3 requires private PostgreSQL, migration, backup, restore, and rollback evidence references. No
database URL, hostname, dump, backup path, or migration log belongs in the gate.
implemented providers.

## Offline workflow

```bash
python scripts/print_pilot_readiness_template.py
python scripts/validate_pilot_readiness.py \
  examples/pilot-readiness/example_pilot_profile.json
python scripts/validate_pilot_readiness.py --strict /path/to/private-placeholder-profile.json
python scripts/generate_pilot_readiness_artifacts.py \
  examples/pilot-readiness/example_pilot_profile.json
```

Generation creates six files under the ignored
`pilot-readiness-output/<safe-profile-name>/` directory:

- `pilot-readiness-report.json`
- `go-no-go.md`
- `launch-checklist.md`
- `operator-signoff.md`
- `known-limitations.md`
- `manifest.json`

Artifacts contain decisions, gate statuses, placeholder signoff fields, findings, limitations,
and hashes only. Generated artifacts are ignored and must not be committed. The committed example
uses fake values only and intentionally returns `NEEDS_REVIEW`.

Any real pilot still requires private customer/GC/Owner evidence, security and operational review,
approved infrastructure, ingress, deployment, monitoring, incident response, rollback, and launch
authorization. Those execution and approval processes remain future work.

C1 provides the companion private-evidence workspace pattern. B9 profiles contain only opaque
evidence refs; actual reports, screenshots, payloads, approvals, and attachments stay in the
separately controlled private system described in
[private pilot evidence](private-pilot-evidence.md).

C2 review and expiry status can support B9 evidence gates. Required evidence that needs review,
has expired, or requires renewal remains a gate blocker; placeholder acceptance is not real pilot
approval.

C3 consumes only the B9 decision status and a placeholder readiness reference. It never copies a
readiness artifact or converts `GO` into real pilot approval.
# Three-mode entry point

Use `make doctor` to reach the pilot readiness tools from the three-mode workflow. Pilot remains
unapproved until private evidence, review, expiry, rollback, and approval work is completed.

B9 may consume the status of a privately reviewed F2 evidence ref, not its report contents. A
passing Sandbox read validation is access evidence only and never pilot or production approval.

F3 provides reference mapping only. B9 evaluates it with all other gates and human-review status;
refs do not make the gate pass automatically.
