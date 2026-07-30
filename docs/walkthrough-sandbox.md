# Sandbox walkthrough

## Who this is for

Use this optional path only when you have authorized Procore sandbox/DMSA access. Finish the
[Demo walkthrough](walkthrough-demo.md) first.

## What must remain private

You need private DMSA client ID and client-secret refs, allowed company/project scope, an admin
authentication ref, and any sandbox smoke evidence ref. Store values in an approved private
provider. Keep real credentials, IDs, names, contacts, domains, paths, and reports outside Git.
Never paste credentials into documentation, examples, issues, or commits.

## Prepare the ignored workspace

```bash
make start
make init-private-workspace
make commands
```

Complete the ignored workspace privately:

- `environment/`: DMSA client ID/secret refs and admin auth ref—not values
- `flow/`: allowed company/project scope placeholders and onboarding state
- `storage/`: contained local root or provider refs

Run Git-isolation validation before recording any private material:

```bash
make private-workspace-git-safety
```

## Run safe planning checks

```bash
make prepare-sandbox
python scripts/check_secret_provider.py
python scripts/check_attachment_storage.py
python scripts/check_sandbox_onboarding.py examples/sandbox-pilot-flow/example_sandbox_flow.json
```

These commands inspect sanitized posture or fake public examples. `make prepare-sandbox` does not
run live smoke by default, resolve secret values, download attachments, or call Procore. A
`needs_configuration` result is expected until private refs and allowed scope are prepared.

See the short [illustrative output](../examples/walkthrough-output/sandbox_expected_output.md).

## Where the live smoke fits

The only live Procore smoke path is the separately documented, manually gated
`scripts/run_sandbox_dmsa_smoke.py` command. Do not run it as part of this walkthrough. It requires
private configuration, allowlists, live-mode gates, an exact confirmation, and explicit operator
authorization. Read [Sandbox smoke tests](sandbox-smoke-tests.md) later.

## Common problems

- Missing refs: configure reference names privately; never put values in public files.
- Wrong target: the private environment must identify a sandbox, never production.
- Missing scope: record only the authorized company/project allowlist privately.
- Storage unavailable: Demo and planning can continue; do not enable a cloud provider casually.

## What to run next

Continue private Sandbox review, or move to the [Pilot walkthrough](walkthrough-pilot.md) only
after authorized sandbox evidence exists. Keep the evidence content private.
