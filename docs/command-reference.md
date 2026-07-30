# Command reference

All commands below are local unless explicitly described otherwise. “Writes” means repository-
ignored local files may be created. None of these commands deploys or approves a pilot.

| Group | Command | What and when | Writes | Procore | External | Demo-safe | Expected output |
|---|---|---|---:|---:|---:|---:|---|
| First run | `make help` | Show the public command menu anytime. | No | No | No | Yes | Short target list |
| First run | `make first-run` | Run doctor, local setup, and mode guidance after install. | No | No | No | Yes | Readiness and next commands |
| First run | `make doctor` | Diagnose selected-mode posture. | No | No | No | Yes | Ready, needs configuration, or blocked |
| Demo Mode | `make setup-demo` | Confirm fixture defaults before trying the app. | No | No | No | Yes | Demo setup summary |
| Demo Mode | `make demo` | Run the fixture-only poll path. | Local DB | No | No | Yes | Synthetic intake summary |
| Demo Mode | `make modes` | Compare all three mode boundaries. | No | No | No | Yes | Concise mode cards |
| Sandbox Mode | `make sandbox-check` | Check fake/offline onboarding posture before private setup. | No | No | No | Yes | Needs-configuration guidance |
| Pilot Mode | `make pilot-check` | Validate fake public pilot artifacts and preflight. | No | No | No | Yes | Placeholder readiness; no approval |
| Private workspace | `make init-private-workspace` | Create ignored placeholder scaffolds when private work begins. | Yes | No | No | Not needed | Relative filenames only |
| Private workspace | `make private-workspace-check` | Validate private workspace structure and Git isolation. | No | No | No | Not needed | Sanitized checks |
| Secret providers | `make secret-provider-check` | Inspect provider posture without resolving or printing values. | No | No | No | Yes | Provider readiness |
| Secret providers | `make secret-refs-check` | Check reference format/readiness. | No | No | No | Yes | Ref-only findings |
| Storage providers | `make storage-provider-check` | Check configured storage posture. | No | No | No | Yes | Sanitized provider status |
| Storage providers | `make local-storage-provider-check` | Exercise contained local storage with fake data. | Temporary/local | No | No | Yes | Local contract result |
| Database readiness | `make database-check` | Inspect database posture without connecting. | No | No | No | Yes | Provider/migration planning status |
| Database readiness | `make migration-safety-check` | Test migrations against disposable SQLite. | Temporary | No | No | Yes | Upgrade/downgrade result |
| Deployment recipes | `make deployment-check` | Validate placeholder recipes offline. | No | No | No | Yes | Recipe findings |
| Deployment recipes | `make deployment-safety-check` | Check that recipes cannot deploy or expose private data. | No | No | No | Yes | Safety result |
| Diagnostics/support | `make diagnostics` | Print sanitized local operator posture. | No | No | No | Yes | Aggregate diagnostics |
| Diagnostics/support | `make support-bundle` | Create an ignored sanitized local bundle for private review. | Yes | No | No | Yes | Relative output names |
| Safety audits | `make public-usability-audit` | Audit docs, commands, tracked files, and ignore rules. | No | No | No | Yes | Pass/warn/fail summary |
| Safety audits | `make safety-check` | Run public data and read-only route audits too. | No | No | No | Yes | Three audit summaries |
| Developer quality | `make quality` | Run the complete offline test and lint suite before a change. | Temporary/local | No | No | Yes | Checks and pytest summary |

Sandbox and Pilot are private/operator-controlled even when their public readiness commands are
safe in Demo Mode. The separately gated sandbox smoke command is intentionally not a friendly
top-level target. Database connectivity, production migrations, deployment, cloud, DNS, TLS, and
webhook registration are also excluded.

What to run next: new users should run `make first-run`; contributors should run `make quality`.
