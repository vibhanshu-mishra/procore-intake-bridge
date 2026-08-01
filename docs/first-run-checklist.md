# First-run checklist

Phase J1 makes this the canonical local-only checklist. Demo Mode is the default safe starting
point and requires no Procore credentials, other secrets, cloud services, or external database.

Run these first, second, and third:

```bash
python3 -m venv .venv            # First
source .venv/bin/activate        # Second
python -m pip install -e ".[dev]" # Third
```

- [ ] Clone the repository and enter its root directory.
- [ ] Create and activate `.venv`.
- [ ] Install with `python -m pip install -e ".[dev]"`.
- [ ] Run `make start` for safe onboarding, doctor, and next-step guidance.
- [ ] If developing, run `make quality`.
- [ ] Run `make try-demo`; it uses fixtures and makes no external calls.
- [ ] Read the [Demo walkthrough](walkthrough-demo.md) and compare only the short illustrative
  output.
- [ ] Run `make commands` to discover deeper commands only when needed.
- [ ] Choose [Sandbox Mode](sandbox-mode.md) or [Pilot Mode](pilot-mode.md) only if needed.
- [ ] Initialize `private-workspace/` only when private preparation is needed.
- [ ] Keep all real credentials, IDs, evidence, approvals, and generated/private files outside Git.
- [ ] Run `make safety-check` before committing.
- [ ] Keep Sandbox, Pilot, and Hosted work separate, private, and manually gated.

Best next command: `make start`. For command details, see the
[command reference](command-reference.md).

Release readiness is a later maintainer workflow, not a first-run step.
Setup performs no package or Docker build, publish, tag, release, or deployment and grants no
production, Pilot, release, deployment, or Procore approval.
The [docs-site guide](docs-site.md) is optional local navigation. MkDocs is not needed for the
first run or Demo Mode, and no documentation site is published.
