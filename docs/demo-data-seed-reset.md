# Demo Data Seed and Reset

J5 links this guide from the setup, Demo, and first-time evaluator paths without changing J2 data
behavior. Documentation preview remains local and performs no deployment, analytics, tracking,
external search, or CDN load.

J4 Demo-ready labels depend on J2's fake, demo-marked local SQLite records. They do not authorize
hosting or customer data. Seed/reset boundaries remain local; J4 performs no deployment, frontend
build, external asset load, analytics, telemetry, or approval.

J3 documents the existing Demo/intake/sync route boundaries without changing J2 seed/reset
behavior. Examples remain fake and local; API documentation makes no live call, uses no external
OpenAPI tooling, and grants no production, Pilot, release, or deployment approval.

Phase J2 provides a repeatable, local-only Demo Mode data experience. It seeds deterministic
fake records into the local SQLite demo database so the dashboard, intake review workspace,
lifecycle views, triage queue, attachment metadata views, and export summaries have useful data.
It does not need Procore credentials, a Procore call, cloud services, or an external database.

## Safety boundary

Seeded records carry an explicit deterministic demo marker. They contain fake values only: no
customer data, real identities, domains, URLs, private paths, secrets, live payloads, attachment
contents, or generated private artifacts. Re-running the seed is idempotent and does not duplicate
the marked records.

Reset is fail-closed. It considers only demo-marked records in the local Demo Mode SQLite
database and requires the exact confirmation phrase `RESET DEMO DATA`. It does not touch records
without the demo marker, the private workspace, Sandbox, Pilot, Hosted, cloud resources, external
databases, or customer data. Print the plan before making a reset:

```bash
make demo-seed-plan
make demo-seed
make demo-data-check
make demo-reset-plan
make demo-reset DEMO_RESET_CONFIRMATION="RESET DEMO DATA"
```

`make try-demo` remains non-destructive: it may inspect or plan demo data, but it does not reset
anything. `make demo-reset` is the only reset command and refuses to act without the exact
confirmation phrase.

Generated plans, inventories, and reports belong only in ignored demo-output roots. J2 grants no
production, Pilot, release, deployment, or Procore approval.

See the [seed plan](demo-seed-plan.md), [reset guide](demo-reset-guide.md), and
[placeholder examples](../examples/demo-data-experience/README.md).
