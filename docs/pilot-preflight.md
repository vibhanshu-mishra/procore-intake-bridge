# Pilot preflight

Pilot preflight assembles local readiness signals for the private workspace, secret and storage
providers, PostgreSQL and migration planning, deployment recipe, diagnostics, evidence manifest
and review, approval packet, rollback, backup, and incident response:

```bash
make pilot-preflight
```

It reads no real private evidence, connects to no service or external database, runs no migration,
deploys nothing, and grants no approval. `pilot_ready_for_private_review` means only that
authorized reviewers may examine the real private materials outside this repository. Launch
remains on hold until that independent review is complete.
