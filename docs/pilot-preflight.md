# Pilot preflight

Sandbox smoke readiness means a reviewed private evidence ref—not report contents—is available.
The live check remains manual, gated, read-only, and outside this preflight. Use
[Sandbox smoke evidence](sandbox-smoke-evidence.md).

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

A separately reviewed private F2 read-validation reference may support Sandbox access posture.
This preflight reads only the reference, never the sanitized report or raw RFI/Submittal data.

F3 supplies a placeholder mapping into preflight. Missing, expired, or unreviewed refs remain
review findings; their presence never makes Pilot readiness pass automatically.

PostgreSQL runtime, maintenance-window, managed-backup, restore-drill, and rollback references are
private preflight evidence. G3 offline checks do not resolve them; live status checks are manually
gated and their success is not Pilot approval.

Selecting a G4 platform style does not satisfy deployment readiness. Preflight must retain
needs-configuration status until private infrastructure, image provenance, HTTPS, providers,
health, scale, monitoring, backup, rollback, and authorization are independently reviewed.
