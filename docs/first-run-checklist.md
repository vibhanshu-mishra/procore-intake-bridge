# First-run checklist

Demo Mode is the default safe starting point and requires no Procore credentials.

- [ ] Clone the repository and enter its root directory.
- [ ] Create and activate `.venv`.
- [ ] Install with `python -m pip install -e ".[dev]"`.
- [ ] Run `make start` for safe onboarding, doctor, and next-step guidance.
- [ ] If developing, run `make quality`.
- [ ] Run `make try-demo`; it uses fixtures and makes no external calls.
- [ ] Run `make commands` to discover deeper commands only when needed.
- [ ] Choose [Sandbox Mode](sandbox-mode.md) or [Pilot Mode](pilot-mode.md) only if needed.
- [ ] Initialize `private-workspace/` only when private preparation is needed.
- [ ] Keep all real credentials, IDs, evidence, approvals, and generated/private files outside Git.
- [ ] Run `make safety-check` before committing.

Best next command: `make start`. For command details, see the
[command reference](command-reference.md).
