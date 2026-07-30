# Public usability audit

Phase E1 checks whether a new user can find the safe Demo, private Sandbox, and private Pilot
paths. It verifies required docs, scripts, examples, Make targets, ignore rules, next-command
guidance, and tracked-file safety patterns.

Run:

```bash
make public-usability-audit
```

- `PASS` means required public guidance or structure is present.
- `WARN` means a non-blocking check could not be completed.
- `FAIL` means a required usability or public-safety condition is missing; the command exits
  nonzero.

The output never prints file contents, secret values, raw environment values, private output, or
absolute local paths. Fix failures by restoring the named public file/link/target, removing a
tracked generated artifact, or extending `.gitignore`, then rerun the audit.

This is a public-repository guardrail, not a security certification or pilot approval. What to run
next: `make safety-check`, then `make quality`.
