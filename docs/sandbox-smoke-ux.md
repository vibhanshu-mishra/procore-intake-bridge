# Sandbox smoke execution UX

Sandbox smoke has two deliberately separate experiences:

1. **Offline planning:** `make sandbox-smoke-explain` and `make sandbox-smoke-preflight`.
2. **Manual live read-only execution:** `python scripts/run_sandbox_dmsa_smoke.py ...`, only after
   private configuration and explicit authorization.

`make prepare-sandbox` is offline planning. It never invokes the live command. Quality, doctor,
walkthroughs, and default targets also never invoke it.

## Before a live run

Privately prepare:

- an approved sandbox DMSA connection with client ID and secret refs
- sandbox-only API posture
- allowed company and project scope
- the separate live-mode and smoke enablement gates
- the exact confirmation phrase printed by `make sandbox-smoke-explain`
- attachment downloads disabled
- a bounded record limit
- an ignored sanitized output destination, if report writing is authorized

Run:

```bash
make sandbox-smoke-explain
make sandbox-smoke-preflight
make sandbox-smoke-evidence-template
```

These commands make no Procore or external calls, resolve no credentials, read no private result,
and write no files.

## What the live check does

After every gate passes, the existing manual command authenticates through DMSA secret refs,
checks the explicitly allowed sandbox project, reads bounded RFI/Submittal samples, and counts
visible attachment metadata. It is read-only.

It does not write to Procore, register webhooks, download attachments by default, persist raw
payloads, or print raw secrets, IDs, URLs, paths, or exception details.

## Interpreting outcomes

- **Blocked:** a mandatory gate did not pass; no live probe should proceed.
- **Failed step:** a bounded read check failed; sensitive exception details remain omitted.
- **Passed steps:** the specific read-only checks succeeded within the configured limit. This is
  not production readiness, customer approval, or pilot approval.

Sanitized output belongs in ignored/private storage. Record only a private evidence reference for
later review. Never copy report contents into Git.

See [Sandbox smoke evidence](sandbox-smoke-evidence.md) and the
[Sandbox walkthrough](walkthrough-sandbox.md).

F2 is a separate, more detailed RFI/Submittal read-validation path; it does not replace or weaken
this smoke UX. See [Sandbox read validation](sandbox-read-validation.md). Neither live command is
run by quality, prepare-sandbox, walkthroughs, release checks, or docs checks.
