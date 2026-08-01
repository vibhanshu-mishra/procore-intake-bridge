# Demo Seed Plan

The J2 seed plan is a non-writing preview for deterministic fake Demo Mode data. Run:

```bash
make demo-seed-plan
```

The plan covers fake intake records, attachment manifests, lifecycle states and events, triage
signals, dashboard counts, export summaries, event-queue fixtures, and sync-run fixtures. Actual
seeding is limited to the local Demo Mode SQLite database and is idempotent.

```bash
make demo-seed
make demo-data-check
```

No Procore credential, cloud service, external database, URL, private path, customer record,
attachment content, or live payload is used. Seed markers make the generated records
distinguishable from every non-demo record. Planning and checking are non-destructive.

J2 is a local demonstration aid. It implies no production, Pilot, release, deployment, or
Procore approval.
