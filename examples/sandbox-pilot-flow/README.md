# Sandbox-to-pilot flow examples

These profiles contain placeholders only. They are safe inputs for local readiness checks and make
no Procore, secret-manager, storage, database, DNS, TLS, cloud, or deployment calls.

```bash
python scripts/check_sandbox_onboarding.py examples/sandbox-pilot-flow/example_sandbox_flow.json
python scripts/check_pilot_preflight.py examples/sandbox-pilot-flow/example_pilot_flow.json
```

Keep actual identifiers, people, evidence, reports, approval records, domains, paths, and secrets
in the ignored private workspace. A pilot result means only “ready for private review”; it never
approves or launches a pilot.
