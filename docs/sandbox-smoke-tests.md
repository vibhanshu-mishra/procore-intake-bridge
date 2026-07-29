# Manually gated sandbox DMSA smoke tests

Phase B1 is an operator-invoked, read-only harness for an approved Procore sandbox or
non-production environment. It checks credential resolution through the existing SecretProvider,
guarded PyProcore authentication, one explicitly allowlisted project, bounded RFI/Submittal reads,
and visible attachment metadata.

It is not automatic sync, production approval, a scheduler, a webhook test, a write path, or a
deployment tool. It never downloads attachments, persists raw Procore payloads, writes
`IntakeRecord` data, or stores raw signed URLs. Production use is intentionally blocked by
default.

## Required manual gates

All gates must pass:

1. `PROCORE_INTAKE_SANDBOX_SMOKE_ENABLED=true`.
2. `PROCORE_INTAKE_LIVE_MODE_ENABLED=true`.
3. `PROCORE_INTAKE_PROCORE_ENVIRONMENT=sandbox`.
4. The exact confirmation phrase is supplied.
5. The deployment profile is non-production, unless the separate production-profile override
   was explicitly reviewed; the connection itself must still be marked sandbox.
6. A local sandbox `DMSAConnection` exists with client-ID and client-secret references.
7. The supplied company matches that connection and the project is in its allowlist.
8. The record limit is at most 10 and attachment downloads remain false.

Create the local connection through the normal connection API using only opaque secret references.
Inject actual sandbox credentials outside the repository through the environment-backed
SecretProvider. Never place values in the connection row, `.env.example`, commands, issues, or
logs.

## Plan and run

The plan is safe anytime and never calls Procore:

```bash
python scripts/print_sandbox_smoke_plan.py
```

After separately configuring the gates and approved sandbox identifiers:

```bash
python scripts/run_sandbox_dmsa_smoke.py \
  --connection-id 1 \
  --company-id COMPANY_ID_PLACEHOLDER \
  --project-id PROJECT_ID_PLACEHOLDER \
  --confirm "I_UNDERSTAND_THIS_IS_READ_ONLY_SANDBOX_ONLY"
```

The report contains gate/readiness outcomes, hashed company/project identifiers, bounded record
counts, hashed item identifiers, status summaries, attachment counts, and hashes of any source
URLs. It excludes credential values, tokens, Authorization headers, raw payloads, project names,
raw URLs, downloads, and absolute output paths.

`passed` means a bounded read step succeeded; `failed` means a probe returned unsuccessfully or
raised an error whose details were suppressed; `blocked` means a safety gate prevented live work;
`skipped` means the connection did not enable that tool.

Sanitized JSON reports go to the ignored `smoke-output/` directory unless `--no-write-report` is
used. Remove that directory when no longer needed, following local retention policy. Do not commit
reports. If a credential leaks anywhere outside the app, revoke or rotate it immediately and do
not paste it into an issue.

Passing this smoke test is not a production guarantee and does not validate production auth,
storage, scheduling, webhooks, operations, or security controls.
B9 consumes only a sanitized B1 sandbox-smoke evidence reference and status. Smoke report contents
must not be embedded in pilot profiles or generated readiness artifacts.

C1 may organize the corresponding smoke evidence ref, never the report contents, identifiers,
payloads, or local report path.
