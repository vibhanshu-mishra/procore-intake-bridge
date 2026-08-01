# Demo Reset Guide

Use reset only when you intentionally want to remove J2-generated records from the local Demo
Mode SQLite database. Always inspect the non-destructive plan first:

```bash
make demo-reset-plan
```

The only reset command is `make demo-reset`. It requires the exact, case-sensitive confirmation
phrase:

```bash
make demo-reset DEMO_RESET_CONFIRMATION="RESET DEMO DATA"
```

Reset removes only records bearing the deterministic J2 demo marker. It fails closed for an
external database, a missing or different confirmation, or unsafe configuration. Records without
the marker are untouched.

Reset never deletes files or records from the private workspace, Sandbox, Pilot, Hosted, cloud
resources, external databases, or customer data. It performs no Procore or external call.
`make try-demo` and `make first-run` are non-destructive and never reset data.

Generated reset plans and reports are local ignored artifacts. A successful local reset does not
imply production, Pilot, release, deployment, or Procore approval.
