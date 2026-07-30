# First-run checklist

Demo Mode is the default safe starting point and requires no Procore credentials.

- [ ] Clone the repository and enter its root directory.
- [ ] Create and activate `.venv`.
- [ ] Install with `python -m pip install -e ".[dev]"`.
- [ ] Run `make first-run` for safe local doctor, setup, and mode checks.
- [ ] If developing, run `make quality`.
- [ ] Run `make setup-demo`.
- [ ] Run `make demo`; it uses fixtures and makes no external calls.
- [ ] Run `make modes`.
- [ ] Choose [Sandbox Mode](sandbox-mode.md) or [Pilot Mode](pilot-mode.md) only if needed.
- [ ] Initialize `private-workspace/` only when private preparation is needed.
- [ ] Keep all real credentials, IDs, evidence, approvals, and generated/private files outside Git.
- [ ] Run `make safety-check` before committing.

What to run next: `make doctor`. For command details, see the
[command reference](command-reference.md).
