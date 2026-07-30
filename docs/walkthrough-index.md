# Guided walkthroughs

Choose one path. Demo is the default; Sandbox and Pilot are optional, private,
operator-controlled journeys.

1. [Demo walkthrough](walkthrough-demo.md) — clone, install, and run synthetic fixtures with no
   Procore credentials, secrets, external database, or external services.
2. [Sandbox walkthrough](walkthrough-sandbox.md) — prepare private DMSA refs and allowed scope,
   then run offline checks. Live smoke is not run by default.
3. [Pilot walkthrough](walkthrough-pilot.md) — prepare private evidence and operational posture
   while keeping approval and launch on hold.

Short illustrative output is under
[`examples/walkthrough-output/`](../examples/walkthrough-output/README.md). It is placeholder-only,
not a captured terminal transcript.

Start with:

```bash
make start
make demo-walkthrough
```

All friendly walkthrough targets are local-only. They print command sequences; they do not call
Procore, connect externally, read private evidence, approve a pilot, or deploy.

After documentation and implementation work is complete, maintainers may separately use the
[release-readiness checklist](release-readiness.md). It is not a user walkthrough and publishes
nothing.
