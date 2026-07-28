# Project status

Current phase: A9 repository polish is complete. A1–A8 behavior and the A9 public-safety
contracts are validated by the current test suite.

- Default runtime: local SQLite with fixture/mock intake.
- Live Procore mode: disabled by default and manually gated.
- Procore writes: none.
- Safe demo scope: synthetic connection/profile creation, fixture dry-runs, stored local mock
  events, onboarding preview, masked local admin views, and readiness reporting.
- Data safety: secret references only, no raw signed URL storage, and ignored generated outputs.

Known limitations include no production tenant authentication/authorization, managed secrets,
production database operations, cloud attachment backend, hosted scheduler, audited logging,
verified production webhook integration, or supported deployment pattern. The default readiness
report intentionally identifies production blockers. This project is not production-ready.

The GC/Owner must approve private DMSA installation and controls project/tool permissions.
Procore Intake Bridge is independent and is not affiliated with or endorsed by Procore.
